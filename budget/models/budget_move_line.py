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
    source_line_id = fields.Many2one(
        comodel_name="budget.move.line",
        string="Source Line",
        help="For virtual lines, references the original appropriation line that created this virtual line",
        ondelete="cascade",
        index=True,
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

        1. For each appropriation line, create one corresponding virtual line
        2. Virtual line has same analytic distribution but opposite balance
        3. Virtual line uses the appropriation virtual account

        This ensures: Total Debits = Total Credits with 1-1 line relationship
        """
        moves = self.env["budget.move"].browse({vals["move_id"] for vals in vals_list})
        container = {"records": self}
        move_container = {"records": moves}

        # กรองเฉพาะ appropriation moves
        appropriation_moves = moves.filtered(lambda m: m.move_type == 'appropriation')

        if appropriation_moves:
            # Technical Note: 1-1 Virtual Line Creation with Source Tracking
            # Each appropriation line gets its own virtual line for clear tracking
            # and easier maintenance. No grouping or consolidation is done.

            # We need to create lines first, then create virtual lines with proper source_line_id
            pass  # Virtual lines will be created in post-processing after regular lines exist

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

            # Technical Note: Post-processing Virtual Line Creation
            # After regular lines are created, create virtual lines with proper source_line_id
            if appropriation_moves:
                virtual_lines_to_create = []
                for line in lines:
                    if line.move_id.move_type == 'appropriation' and not line.is_virtual_line:
                        # Create virtual line with source_line_id pointing to this line
                        virtual_vals = {
                            'balance': -line.balance,  # Opposite balance for double-entry
                            'analytic_distribution': line.analytic_distribution.copy() if line.analytic_distribution else {},
                            'move_id': line.move_id.id,
                            'account_id': line.move_id.appropriation_account_id.id,
                            'is_virtual_line': True,
                            'source_line_id': line.id,  # Link to source line
                        }
                        virtual_lines_to_create.append(virtual_vals)

                if virtual_lines_to_create:
                    # Create virtual lines with skip_virtual_update to avoid recursion
                    self.with_context(skip_virtual_update=True).create(virtual_lines_to_create)

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
        Technical Note: Handling Virtual Lines on Update (source_line_id tracking)

        When appropriation lines are modified (balance or analytic distribution),
        we update only the linked virtual lines using source_line_id field.
        The process:

        1. Find virtual lines linked to modified regular lines via source_line_id
        2. Update existing virtual lines or create new ones if missing
        3. Each virtual line maintains opposite balance and same analytics

        This ensures efficient targeted updates with maintained line relationships.
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

                # Technical Note: Targeted Virtual Line Updates using source_line_id
                # Only update virtual lines linked to the modified appropriation lines
                for line in appropriation_lines:
                    # Find and update the virtual line linked to this regular line
                    virtual_line = self.search([
                        ('source_line_id', '=', line.id),
                        ('is_virtual_line', '=', True)
                    ], limit=1)

                    if virtual_line:
                        # Update existing virtual line to match source line
                        virtual_vals = {
                            'balance': -line.balance,  # Opposite balance for double-entry
                            'analytic_distribution': line.analytic_distribution.copy() if line.analytic_distribution else {},
                        }
                        virtual_line.with_context(skip_virtual_update=True).write(virtual_vals)
                    else:
                        # Create new virtual line if it doesn't exist
                        virtual_vals = {
                            'balance': -line.balance,
                            'analytic_distribution': line.analytic_distribution.copy() if line.analytic_distribution else {},
                            'move_id': line.move_id.id,
                            'account_id': line.move_id.appropriation_account_id.id,
                            'is_virtual_line': True,
                            'source_line_id': line.id,  # Link to source line
                        }
                        self.with_context(skip_virtual_update=True).create(virtual_vals)

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
        Technical Note: Virtual Line Management on Deletion (source_line_id tracking)

        When deleting appropriation lines, their linked virtual lines are also deleted
        automatically using the source_line_id field. This method:

        1. Finds virtual lines linked to appropriation lines being deleted
        2. Deletes both regular lines and their linked virtual lines
        3. Maintains proper accounting balance through precise deletion

        This prevents "move is not balanced" errors with targeted deletions.
        """
        # Technical Note: Targeted Virtual Line Deletion using source_line_id
        # Delete virtual lines linked to the appropriation lines being deleted
        virtual_lines_to_delete = self.env['budget.move.line']
        for line in self:
            if line.move_id.move_type == 'appropriation' and not line.is_virtual_line:
                # Find virtual lines linked to this line
                virtual_lines = self.search([
                    ('source_line_id', '=', line.id),
                    ('is_virtual_line', '=', True)
                ])
                virtual_lines_to_delete |= virtual_lines

        # Delete the lines and their linked virtual lines
        if virtual_lines_to_delete:
            virtual_lines_to_delete.with_context(skip_virtual_update=True).unlink()

        result = super().unlink()

        return result

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        if 'hide_virtual_lines' in self.env.context:
            domain = domain or []
            domain.append(('is_virtual_line', '=', False))
        return super().search_read(domain, fields, offset, limit, order)
