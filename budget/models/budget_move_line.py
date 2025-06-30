import logging

from contextlib import ExitStack, contextmanager
from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class BudgetMoveLine(models.Model):
    _name = "budget.move.line"
    _description = "Budget Move Line"
    _inherit = ["analytic.distribution.mixin", "mail.thread"]
    _order = "date desc, move_name desc, id"

    move_id = fields.Many2one(
        comodel_name="budget.move",
        string="Budget Move",
        copy=True,
        required=True,
        readonly=True,
        index=True,
        auto_join=True,
        ondelete="cascade",
    )
    move_name = fields.Char(
        string='Number',
        related='move_id.name', store=True,
        index='btree',
    )
    date = fields.Date(related="move_id.date", store=True)
    code = fields.Char("รหัสงบประมาณ", related="account_id.code", store=True, tracking=True)
    name = fields.Char("ชื่อรายการ", related="account_id.name", store=True, tracking=True)
    account_id = fields.Many2one(
        comodel_name="budget.account",
        index=True,
        required=True,
        # TODO: ต้องกรองข้อมูลเฉพาะรหัสงบประมาณ ที่อยู่ภายใต้กองทุนที่เลือกเท่านั้น
        domain="[('budget_type', '=', budget_type)]",
        tracking=True,
    )
    budget_type = fields.Selection(
        related="move_id.journal_id.default_budget_type", store=True, readonly=True
    )
    balance = fields.Float(
        digits="Budget Precision",
        help="Amount",
        readonly=False,
        tracking=True,
    )
    credit = fields.Float(
        readonly=False,
        digits="Budget Precision",
        store=True,
        compute="_compute_balance_credit_debit",
    )
    debit = fields.Float(
        readonly=False,
        digits="Budget Precision",
        store=True,
        compute="_compute_balance_credit_debit",
    )
    note = fields.Text(tracking=True)
    department_analytic_id = fields.Many2one(
        "account.analytic.account",
        domain=[("root_plan_id.code", "=", "departments")],
        compute="_compute_department_analytic",
        store=True,
        readonly=False,
    )

    # === Parent fields === #
    source_analytic_id = fields.Many2one(
        related="move_id.source_analytic_id", store=True
    )
    date_range_fy_id = fields.Many2one(related="move_id.date_range_fy_id", store=True)
    parent_state = fields.Selection(related="move_id.state", store=True)
    journal_id = fields.Many2one(
        related="move_id.journal_id",
        store=True,
        precompute=True,
        index=True,
        copy=False,
    )
    company_id = fields.Many2one(related="move_id.company_id", store=True)
    currency_id = fields.Many2one(related="company_id.currency_id", store=True)
    company_currency_id = fields.Many2one(related="company_id.currency_id", store=True)
    fund_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="กองทุน",
        domain=[("root_plan_id.code", "=", "funds")],
    )
    is_virtual_line = fields.Boolean(
        string='Is Virtual Line',
        default=False,
        help='Line created automatically for double-entry'
    )

    @api.depends('move_id', 'move_id.department_analytic_id', 'move_id.move_type')
    def _compute_department_analytic(self):
        for line in self:
            if line.move_id and line.move_id.move_type == 'appropriation':
                # ใช้ department จาก move สำหรับ appropriation
                line.department_analytic_id = line.move_id.department_analytic_id
            # สำหรับ move types อื่น ให้ผู้ใช้เลือกเอง

    @api.depends("balance")
    def _compute_balance_credit_debit(self):
        for line in self:
            if line.balance >= 0:
                line.debit = line.balance
                line.credit = 0
            else:
                line.credit = -line.balance
                line.debit = 0

    @api.onchange("balance")
    def _inverse_balance(self):
        for line in self:
            if line.balance >= 0:
                line.debit = line.balance
                line.credit = 0
            else:
                line.credit = -line.balance
                line.debit = 0

    @api.model_create_multi
    def create(self, vals_list):
        moves = self.env["budget.move"].browse({vals["move_id"] for vals in vals_list})
        container = {"records": self}
        move_container = {"records": moves}

        # กรองเฉพาะ appropriation moves
        appropriation_moves = moves.filtered(lambda m: m.move_type == 'appropriation')

        if appropriation_moves:
            # Group appropriation lines by move and dimensions
            virtual_lines_by_move = {}

            for vals in vals_list:
                move = self.env["budget.move"].browse(vals["move_id"])
                if move.move_type == 'appropriation' and not vals.get('is_virtual_line'):
                    # Create key based on dimensions - convert dict to frozenset for hashability
                    analytic_dist = vals.get('analytic_distribution', {})
                    if isinstance(analytic_dist, dict):
                        analytic_key = frozenset(analytic_dist.items())
                    else:
                        analytic_key = frozenset()

                    dimension_key = (
                        vals.get('move_id'),
                        analytic_key,
                    )

                    if dimension_key not in virtual_lines_by_move:
                        virtual_lines_by_move[dimension_key] = {
                            'balance': 0.0,
                            'vals': vals.copy(),
                            'move': move
                        }

                    # Sum the balance
                    virtual_lines_by_move[dimension_key]['balance'] += vals.get('balance', 0.0)

            # Create consolidated virtual lines
            for dimension_key, virtual_data in virtual_lines_by_move.items():
                virtual_vals = self._prepare_virtual_line_vals(virtual_data['vals'], virtual_data['move'])
                # Set the consolidated negative balance
                virtual_vals['balance'] = -virtual_data['balance']
                vals_list.append(virtual_vals)

        with moves._check_balanced(move_container), ExitStack() as exit_stack:
            lines = super().create([self._sanitize_vals(vals) for vals in vals_list])
            exit_stack.enter_context(
                self.env.protecting(
                    [
                        protected
                        for vals, line in zip(vals_list, lines)
                        for protected in self.env["budget.move"]._get_protected_vals(
                            vals, line
                        )
                    ]
                )
            )
            container["records"] = lines

        return lines

    def _prepare_virtual_line_vals(self, original_vals, move):
        """Prepare values for virtual line (opposite entry)"""
        virtual_vals = original_vals.copy()

        # สลับเครื่องหมายของ balance
        virtual_vals['balance'] = -original_vals.get('balance', 0.0)

        # ใช้ virtual account
        virtual_vals['account_id'] = move.appropriation_account_id.id

        # Mark as virtual line
        virtual_vals['is_virtual_line'] = True

        # Copy analytic distribution
        if 'analytic_distribution' in original_vals:
            virtual_vals['analytic_distribution'] = original_vals['analytic_distribution'].copy()

        return virtual_vals

    def write(self, vals):
        if not vals:
            return True
        line_to_write = self
        vals = self._sanitize_vals(vals)

        # Handle appropriation line updates - need to update virtual lines
        if not self.env.context.get('skip_virtual_update'):
            balance_update = 'balance' in vals
            analytic_update = 'analytic_distribution' in vals

            appropriation_lines = self.filtered(lambda l: l.move_id.move_type == 'appropriation' and not l.is_virtual_line)

            if (balance_update or analytic_update) and appropriation_lines:
                # Group lines by move to handle virtual line updates per move
                moves_to_update = appropriation_lines.mapped('move_id')

                # Store tracking info before write
                tracking_info = {}
                if not self.env.context.get("tracking_disable", False):
                    tracking_fields = []
                    for field_name in vals:
                        field = self._fields.get(field_name)
                        if field and hasattr(field, "tracking") and field.tracking:
                            tracking_fields.append(field_name)

                    if tracking_fields:
                        ref_fields = self.fields_get(tracking_fields)
                        for line in appropriation_lines:
                            tracking_info[line.id] = {
                                'ref_fields': ref_fields,
                                'initial_values': {field: line[field] for field in tracking_fields}
                            }

                # Apply the write
                result = super().write(vals)

                # Update virtual lines for each affected move
                for move in moves_to_update:
                    # Delete existing virtual lines
                    move.line_ids.filtered(lambda l: l.is_virtual_line).unlink()

                    # Recalculate consolidated virtual lines
                    virtual_lines_data = {}
                    for line in move.line_ids.filtered(lambda l: not l.is_virtual_line):
                        # Create key based on analytic distribution
                        dimension_key = frozenset(line.analytic_distribution.items()) if line.analytic_distribution else frozenset()

                        if dimension_key not in virtual_lines_data:
                            virtual_lines_data[dimension_key] = {
                                'balance': 0.0,
                                'analytic_distribution': line.analytic_distribution.copy() if line.analytic_distribution else {},
                                'move_id': move.id,
                                'account_id': move.appropriation_account_id.id,
                                'is_virtual_line': True,
                            }

                        virtual_lines_data[dimension_key]['balance'] += line.balance

                    # Create consolidated virtual lines with negative balance
                    for virtual_data in virtual_lines_data.values():
                        virtual_data['balance'] = -virtual_data['balance']
                        self.with_context(skip_virtual_update=True).create(virtual_data)

                # Handle tracking
                if tracking_info and not self.env.context.get("tracking_disable", False):
                    for line in appropriation_lines:
                        if line.id in tracking_info:
                            tracking_value_ids = line._mail_track(
                                tracking_info[line.id]['ref_fields'],
                                tracking_info[line.id]['initial_values']
                            )[1]
                            if tracking_value_ids:
                                msg = _(
                                    "Budget Item %s updated",
                                    line._get_html_link(title=f"#{line.id}"),
                                )
                                line.move_id._message_log(
                                    body=msg, tracking_value_ids=tracking_value_ids
                                )

                return result

        # Normal write process

        if not self.env.context.get("tracking_disable", False):
            # Get trackable fields from vals
            tracking_fields = []
            for field_name in vals:
                field = self._fields.get(field_name)
                if field and hasattr(field, "tracking") and field.tracking:
                    tracking_fields.append(field_name)

            # Store initial values for tracking
            move_initial_values = {}
            if tracking_fields:
                ref_fields = self.fields_get(tracking_fields)
                for line in self:
                    if line.move_id.id not in move_initial_values:
                        move_initial_values[line.move_id.id] = {}
                    for field in tracking_fields:
                        move_initial_values[line.move_id.id][field] = line[field]

        # Skip updating virtual lines if already handled
        if self.env.context.get('skip_virtual_update'):
            result = super().write(vals)
        else:
            result = super().write(vals)

        if not self.env.context.get("tracking_disable", False):
            for move_id, initial_values in move_initial_values.items():
                for line in self.filtered(lambda l: l.move_id.id == move_id):
                    tracking_value_ids = line._mail_track(
                        ref_fields, initial_values
                    )[1]
                    if tracking_value_ids:
                        msg = _(
                            "Budget Item %s updated",
                            line._get_html_link(title=f"#{line.id}"),
                        )
                        line.move_id._message_log(
                            body=msg, tracking_value_ids=tracking_value_ids
                        )
        return result

    def _sanitize_vals(self, vals):
        return vals

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        if 'hide_virtual_lines' in self.env.context:
            domain = domain or []
            domain.append(('is_virtual_line', '=', False))
        return super().search_read(domain, fields, offset, limit, order)
