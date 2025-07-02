import logging

from contextlib import ExitStack, contextmanager
from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class BudgetMoveLine(models.Model):
    """
    Budget Move Line - Individual line item within budget moves for detailed accounting.

    Business Purpose:
        Represents individual accounting entries within budget moves, implementing
        double-entry bookkeeping with detailed analytic distribution for precise
        budget tracking and reporting.

    Key Features:
        • Double-entry accounting with debit/credit balance tracking
        • Complete 4D analytic distribution (Activities, Departments, Funds, Sources)
        • Virtual line support for appropriation balancing entries
        • Hierarchical analytic matching for budget availability calculations
        • Integration with budget commitments through analytic matching

    Line Types by Move Type:
        **Appropriation Lines:**
        • Regular lines: Actual budget allocation amounts
        • Virtual lines: Balancing entries for double-entry system
        • Positive balance: Increases budget availability

        **Consumption Lines:**
        • Track actual budget usage from commitments
        • Negative balance: Reduces budget availability
        • Links to specific budget commitments

        **Entry Lines:**
        • Manual adjustments and corrections
        • Budget transfers between accounts
        • Can be positive or negative based on operation

    Analytic Distribution:
        Each line maintains complete 4D analytic breakdown:
        • Budget Account: Specific chart of accounts item
        • Activity: งานบริหาร > งานสำนักงาน > งานธุรการ
        • Department: สำนักงานอธิการบดี > งานบุคคล
        • Fund: เงินรายได้ > เงินค่าบำรุง
        • Source: เงินแผ่นดิน, เงินนอกงบประมาณ
    """
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
    currency_id = fields.Many2one(string="Currency", related="company_id.currency_id", store=True)
    company_currency_id = fields.Many2one(string="Company Currency", related="company_id.currency_id", store=True)
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
        """
        Technical Note: Balance to Debit/Credit Conversion

        Budget moves use a single 'balance' field that gets split into:
        - Positive balance → Debit column (increases budget)
        - Negative balance → Credit column (decreases budget)

        For appropriations:
        - Regular lines: Positive balance (debit) = budget allocation
        - Virtual lines: Negative balance (credit) = balancing entry
        """
        for line in self:
            _logger.info(line)
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
        """
        Technical Note: Virtual Line Creation for Budget Appropriations

        For appropriation moves, this method automatically creates balancing entries (virtual lines)
        to maintain double-entry bookkeeping. The process:

        1. Groups regular lines by their analytic dimensions
        2. Sums balances for lines with identical dimensions
        3. Creates one virtual line per dimension group with opposite balance

        This ensures: Total Debits = Total Credits
        """
        moves = self.env["budget.move"].browse({vals["move_id"] for vals in vals_list})
        container = {"records": self}
        move_container = {"records": moves}

        # กรองเฉพาะ appropriation moves
        appropriation_moves = moves.filtered(lambda m: m.move_type == 'appropriation')

        if appropriation_moves:
            # Technical Note: Grouping Logic
            # We group lines by (move_id, analytic_distribution) to consolidate
            # multiple lines with same dimensions into single virtual lines
            virtual_lines_by_move = {}

            for vals in vals_list:
                move = self.env["budget.move"].browse(vals["move_id"])
                if move.move_type == 'appropriation' and not vals.get('is_virtual_line'):
                    # Technical Note: Analytic Distribution Key
                    # Convert dict to frozenset for use as dictionary key
                    # This allows grouping by the 4D analytic dimensions:
                    # - Activities, Departments, Funds, Projects
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

                    # Sum balances for lines with identical dimensions
                    virtual_lines_by_move[dimension_key]['balance'] += vals.get('balance', 0.0)

            # Technical Note: Virtual Line Creation
            # For each dimension group, create one virtual line with:
            # - Same analytic distribution
            # - Opposite balance (for double-entry)
            # - Virtual account from appropriation settings
            for dimension_key, virtual_data in virtual_lines_by_move.items():
                # Create a copy of vals with the summed balance
                summed_vals = virtual_data['vals'].copy()
                summed_vals['balance'] = virtual_data['balance']
                # _prepare_virtual_line_vals will negate the balance
                virtual_vals = self._prepare_virtual_line_vals(summed_vals, virtual_data['move'])
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
        """
        Technical Note: Handling Virtual Lines on Update

        When appropriation lines are modified (balance or analytic distribution),
        we must recreate all virtual lines to maintain the accounting balance.
        The process:

        1. Delete all existing virtual lines for affected moves
        2. Recalculate groupings based on updated values
        3. Create new virtual lines with correct balances

        This ensures the move remains balanced after any changes.
        """
        if not vals:
            return True
        line_to_write = self
        vals = self._sanitize_vals(vals)

        # Technical Note: Virtual Line Update Logic
        # skip_virtual_update context prevents recursive updates when
        # we're creating/updating virtual lines themselves
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

                # Technical Note: Virtual Line Recreation Process
                # For each move, we completely recreate virtual lines to ensure
                # they accurately reflect the current state of regular lines
                for move in moves_to_update:
                    # Step 1: Delete all existing virtual lines
                    move.line_ids.filtered(lambda l: l.is_virtual_line).unlink()

                    # Step 2: Group regular lines by analytic dimensions
                    # This consolidates multiple lines with same dimensions
                    virtual_lines_data = {}
                    for line in move.line_ids.filtered(lambda l: not l.is_virtual_line):
                        # Technical Note: Dimension Key Creation
                        # frozenset allows using dict as dictionary key
                        # Empty dict becomes empty frozenset
                        dimension_key = frozenset(line.analytic_distribution.items()) if line.analytic_distribution else frozenset()

                        if dimension_key not in virtual_lines_data:
                            virtual_lines_data[dimension_key] = {
                                'balance': 0.0,
                                'analytic_distribution': line.analytic_distribution.copy() if line.analytic_distribution else {},
                                'move_id': move.id,
                                'account_id': move.appropriation_account_id.id,  # Virtual account
                                'is_virtual_line': True,
                            }

                        # Accumulate balances for same dimensions
                        virtual_lines_data[dimension_key]['balance'] += line.balance

                    # Step 3: Create new virtual lines with opposite balances
                    for virtual_data in virtual_lines_data.values():
                        # Negate balance: if regular lines = +100 (debit), virtual = -100 (credit)
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

    def unlink(self):
        """
        Technical Note: Virtual Line Management on Deletion

        When deleting appropriation lines, virtual lines must be recreated to
        maintain the accounting balance. This method:

        1. Identifies affected appropriation moves before deletion
        2. Deletes the requested lines
        3. Recreates virtual lines for remaining regular lines

        This prevents "move is not balanced" errors when deleting lines.
        """
        # Technical Note: Pre-deletion Move Collection
        # We must collect affected moves before deletion because after
        # super().unlink(), the lines no longer exist to check their moves
        appropriation_moves = set()
        for line in self:
            if line.move_id.move_type == 'appropriation' and not line.is_virtual_line:
                appropriation_moves.add(line.move_id)

        # Delete the lines
        result = super().unlink()

        # Technical Note: Post-deletion Virtual Line Recreation
        # Only process moves that still exist (not deleted with cascade)
        for move in appropriation_moves:
            if move.exists():  # Check if move still exists
                # Step 1: Remove all virtual lines
                move.line_ids.filtered(lambda l: l.is_virtual_line).unlink()

                # Step 2: Regroup remaining lines by dimensions
                virtual_lines_data = {}
                for line in move.line_ids.filtered(lambda l: not l.is_virtual_line):
                    # Group by analytic distribution
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

                # Step 3: Create new virtual lines
                for virtual_data in virtual_lines_data.values():
                    # Negate for double-entry balance
                    virtual_data['balance'] = -virtual_data['balance']
                    self.with_context(skip_virtual_update=True).create(virtual_data)

        return result

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        if 'hide_virtual_lines' in self.env.context:
            domain = domain or []
            domain.append(('is_virtual_line', '=', False))
        return super().search_read(domain, fields, offset, limit, order)
