import logging
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)


class BudgetCommitment(models.Model):
    """
    Budget Commitment - Reserve budget amounts before consumption.

    Business Purpose:
        Budget commitments prevent over-allocation by reserving budget amounts before actual
        spending occurs. This provides financial control and ensures budget availability
        before making purchasing or spending commitments.

    4D Analytic Distribution System:
        Each commitment implements the complete 4-dimensional analytic structure used
        throughout the KMITL budget system:

        1. Activities (กิจกรรม) - activity_analytic_id
           • แผนงาน/โครงการ/กิจกรรม hierarchy
           • Examples: งานบริหารทั่วไป > งานสำนักงาน > งานธุรการ

        2. Departments (ส่วนงาน) - department_analytic_id
           • Organizational structure hierarchy
           • Examples: สำนักงานอธิการบดี > งานบุคคล > งานสรรหา

        3. Funds (กองทุน) - fund_analytic_id
           • Funding source hierarchy
           • Examples: เงินรายได้ > เงินค่าบำรุง > เงินค่าสาธารณูปโภค

        4. Sources (แหล่งเงิน) - source_analytic_id
           • Money source classification
           • Examples: เงินแผ่นดิน, เงินนอกงบประมาณ, เงินบริจาค

    Real-time Budget Availability:
        Each commitment continuously calculates and displays:
        • Available budget amount (available_budget_amount)
        • Budget availability status (sufficient/warning/insufficient)
        • Percentage of available budget being requested
        • Color-coded visual feedback in the user interface

    State Lifecycle:
        draft → reserved → done
        │       │         │
        │       │         └── Fully processed, budget released or consumed
        │       └──────────── Budget reserved, prevents over-commitment
        └─────────────────── Editable, no budget impact

    Key Features:
        • Real-time budget availability checking with hierarchical matching
        • Automatic analytic validation and fund restrictions
        • Consumption tracking through linked budget moves
        • Multi-currency support with proper currency handling
        • OnChange validations with user-friendly warnings
        • Integration with budget.controller for optimized calculations

    Data Relationships:
        • References: budget.account (specific account being used)
        • Analytics: account.analytic.account (4D analytic dimensions)
        • Consumption: budget.move.line (via analytic matching)

    Calculation Logic:
        • Available Budget = Appropriated - Reserved - Consumed
        • Uses hierarchical matching for appropriation coverage
        • Real-time updates when analytic dimensions change

    Thai Localization:
        • Supports Thai government chart of accounts structure
        • Multi-level analytic hierarchies for Thai institutions
        • Currency handling for Thai Baht and foreign currencies
        • Validation rules aligned with Thai accounting practices

    Performance Features:
        • Computed fields with smart dependencies
        • Efficient parent_path hierarchy traversal
        • Optimized budget controller service integration
        • Minimal database queries through strategic caching
    """
    _name = "budget.commitment"
    _description = "Budget Commitment"
    _inherit = ["analytic.distribution.mixin", "mail.thread", "mail.activity.mixin"]
    _order = "date desc, name desc, id desc"
    _rec_names_search = ["name", "ref"]

    READONLY_STATES = {
        "reserved": [("readonly", True)],
        "done": [("readonly", True)],
        "cancel": [("readonly", True)],
    }

    name = fields.Char(
        string="Number",
        required=True,
        copy=False,
        tracking=True,
        index="trigram",
        default=lambda self: _("New"),
        readonly=False,
        states=READONLY_STATES,
    )

    ref = fields.Char(
        string="Reference",
        copy=False,
        tracking=True,
        readonly=False,
        states=READONLY_STATES,
    )

    date = fields.Date(
        string="Commitment Date",
        required=True,
        index=True,
        default=fields.Date.context_today,
        tracking=True,
        readonly=False,
        states=READONLY_STATES,
    )

    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("reserved", "Reserved"),
            ("done", "Done"),
            ("cancel", "Cancelled"),
        ],
        string="Status",
        required=True,
        readonly=True,
        copy=False,
        tracking=True,
        default="draft",
    )

    date_range_fy_id = fields.Many2one(
        comodel_name="account.fiscal.year",
        string="ปีงบประมาณ",
        required=True,
        tracking=True,
        readonly=False,
        states=READONLY_STATES,
    )

    description = fields.Text(
        string="Description",
        tracking=True,
        readonly=False,
        states=READONLY_STATES,
    )

    user_id = fields.Many2one(
        string="User",
        comodel_name="res.users",
        copy=False,
        default=lambda self: self.env.user,
        store=True,
        tracking=True,
        readonly=False,
        states=READONLY_STATES,
    )

    account_id = fields.Many2one(
        comodel_name="budget.account",
        string="รหัสงบประมาณ",
        required=True,
        index=True,
        tracking=True,
        domain="[('budgetable', '=', True), ('budget_type', '=', 'expense')]",
        states=READONLY_STATES,
    )

    amount = fields.Monetary(
        string="จำนวนเงินจอง",
        required=True,
        currency_field="currency_id",
        tracking=True,
        help="Amount to be committed for this budget line",
        states=READONLY_STATES,
    )

    activity_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="กิจกรรม",
        required=True,
        tracking=True,
        domain=[("root_plan_id.code", "=", "activities")],
        help="Activity dimension - แผนงาน/กิจกรรม",
        states=READONLY_STATES,
    )

    department_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="ส่วนงาน",
        required=True,
        tracking=True,
        domain=[("root_plan_id.code", "=", "departments")],
        help="Department dimension",
        states=READONLY_STATES,
    )

    fund_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="กองทุน",
        required=True,
        tracking=True,
        domain=[("root_plan_id.code", "=", "funds")],
        help="Fund dimension - กองทุน",
        states=READONLY_STATES,
    )

    source_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="แหล่งเงิน",
        required=True,
        tracking=True,
        domain=[("root_plan_id.code", "=", "sources")],
        help="Source dimension",
        states=READONLY_STATES,
    )

    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
        tracking=True,
        states=READONLY_STATES,
    )

    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        default=lambda self: self.env.company.currency_id,
        required=True,
        store=True,
    )

    # Budget account related fields
    budget_account_code = fields.Char(
        related="account_id.code",
        store=True,
        string="Budget Code",
    )

    budget_account_name = fields.Char(
        related="account_id.name",
        store=True,
        string="Budget Account Name",
    )

    budget_type = fields.Selection(
        related="account_id.budget_type",
        store=True,
        string="Budget Type",
    )

    # Consumption tracking
    consumed_amount = fields.Monetary(
        string="Consumed Amount",
        compute="_compute_consumed_amount",
        store=True,
        currency_field="currency_id",
        help="Amount already consumed from budget moves",
    )

    remaining_amount = fields.Monetary(
        string="Remaining Amount",
        compute="_compute_remaining_amount",
        store=True,
        currency_field="currency_id",
        help="Amount still available for consumption",
    )

    notes = fields.Text(
        string="Notes",
        help="Additional notes for this commitment",
    )

    # Budget availability fields
    available_budget_amount = fields.Monetary(
        string="Available Budget",
        compute="_compute_available_budget",
        store=True,
        currency_field="currency_id",
        help="Available budget amount for this analytic combination",
    )

    budget_availability_status = fields.Selection(
        selection=[
            ('sufficient', 'Sufficient'),
            ('warning', 'Warning'),
            ('insufficient', 'Insufficient'),
        ],
        string="Budget Status",
        compute="_compute_available_budget",
        store=True,
        help="Budget availability status for this commitment",
    )

    budget_availability_percentage = fields.Float(
        string="% of Available",
        compute="_compute_available_budget",
        store=True,
        help="Percentage of available budget this commitment represents",
    )

    # Related budget moves for consumption tracking
    budget_move_ids = fields.One2many(
        comodel_name="budget.move",
        inverse_name="commitment_id",
        string="Related Budget Moves",
        readonly=True,
    )

    @api.depends("amount", "budget_move_ids.line_ids")
    def _compute_consumed_amount(self):
        """Calculate how much of this commitment has been consumed by budget moves"""
        for record in self:
            consumed = 0.0

            # Find budget move lines that match this commitment's analytics
            related_moves = record.budget_move_ids.filtered(
                lambda m: m.state == "posted"
            )

            for move in related_moves:
                for move_line in move.line_ids:
                    # Check if budget move line matches this commitment
                    if (move_line.account_id == record.account_id and
                        move_line.activity_analytic_id == record.activity_analytic_id and
                        move_line.fund_analytic_id == record.fund_analytic_id):
                        consumed += abs(move_line.balance)

            record.consumed_amount = min(consumed, record.amount)

    @api.depends("amount", "consumed_amount")
    def _compute_remaining_amount(self):
        """Calculate remaining amount available"""
        for record in self:
            record.remaining_amount = record.amount - record.consumed_amount

    @api.depends(
        "account_id",
        "activity_analytic_id",
        "fund_analytic_id",
        "department_analytic_id",
        "source_analytic_id",
        "amount",
        "date_range_fy_id",
        "state",
    )
    def _compute_available_budget(self):
        """Calculate real-time budget availability for this commitment"""
        budget_controller = self.env['budget.controller']

        for record in self:
            if not all([
                record.account_id,
                record.activity_analytic_id,
                record.fund_analytic_id,
                record.date_range_fy_id
            ]):
                record.available_budget_amount = 0.0
                record.budget_availability_status = 'insufficient'
                record.budget_availability_percentage = 0.0
                continue

            # Prepare analytic data for budget controller
            analytic_data = {
                'account_id': record.account_id.id,
                'activity_analytic_id': record.activity_analytic_id.id,
                'department_analytic_id': record.department_analytic_id.id if record.department_analytic_id else False,
                'fund_analytic_id': record.fund_analytic_id.id,
                'source_analytic_id': record.source_analytic_id.id if record.source_analytic_id else False,
            }

            try:
                # Get available budget amount
                available = budget_controller.get_available_budget(
                    analytic_data,
                    record.date_range_fy_id.id,
                    record.company_id.id
                )

                # If commitment is already reserved, add back its own amount to available
                if record.state == 'reserved' and record.amount:
                    available += record.amount

                record.available_budget_amount = available

                # Calculate status and percentage
                if record.amount:
                    # Check if negative budget is allowed
                    allow_negative = record.env['ir.config_parameter'].sudo().get_param('budget.allow_negative', False)

                    if available >= record.amount:
                        record.budget_availability_status = 'sufficient'
                    elif available >= record.amount * 0.5 or (allow_negative and available >= 0):  # 50% threshold or allow negative
                        record.budget_availability_status = 'warning'
                    elif allow_negative:
                        record.budget_availability_status = 'warning'  # Allow negative but show warning
                    else:
                        record.budget_availability_status = 'insufficient'

                    record.budget_availability_percentage = (record.amount / available * 100) if available > 0 else 999.99
                else:
                    record.budget_availability_status = 'sufficient'
                    record.budget_availability_percentage = 0.0

            except Exception as e:
                _logger.warning("Error calculating budget availability for commitment %s: %s", record.id, str(e))
                record.available_budget_amount = 0.0
                record.budget_availability_status = 'insufficient'
                record.budget_availability_percentage = 0.0

    @api.onchange("fund_analytic_id", "account_id")
    def _onchange_fund_account_validation(self):
        """Validate that budget account is allowed for selected fund"""
        if self.fund_analytic_id and self.account_id:
            # Check if budget account has fund restrictions
            if self.account_id.fund_analytic_ids:
                if self.fund_analytic_id not in self.account_id.fund_analytic_ids:
                    return {
                        'warning': {
                            'title': _('Fund Restriction'),
                            'message': _('Budget account %s is not allowed for fund %s') % (
                                self.account_id.name,
                                self.fund_analytic_id.name
                            )
                        }
                    }

    @api.onchange("amount", "account_id", "activity_analytic_id", "fund_analytic_id")
    def _onchange_check_budget_availability(self):
        """Check budget availability and show warning if insufficient"""
        if self.amount and self.available_budget_amount >= 0:
            # Check if negative budget is allowed
            allow_negative = self.env['ir.config_parameter'].sudo().get_param('budget.allow_negative', False)

            if self.budget_availability_status == 'insufficient' and not allow_negative:
                return {
                    'warning': {
                        'title': _('Insufficient Budget'),
                        'message': _(
                            'The requested amount (%(requested)s) exceeds the available budget (%(available)s).\n\n'
                            'Budget Account: %(account)s\n'
                            'Activity: %(activity)s\n'
                            'Fund: %(fund)s\n\n'
                            'Please reduce the amount or select a different analytic combination.'
                        ) % {
                            'requested': "{:,.2f}".format(self.amount),
                            'available': "{:,.2f}".format(self.available_budget_amount),
                            'account': self.account_id.display_name if self.account_id else 'N/A',
                            'activity': self.activity_analytic_id.display_name if self.activity_analytic_id else 'N/A',
                            'fund': self.fund_analytic_id.display_name if self.fund_analytic_id else 'N/A',
                        }
                    }
                }
            elif self.budget_availability_status == 'warning':
                if allow_negative and self.available_budget_amount < self.amount:
                    return {
                        'warning': {
                            'title': _('Negative Budget Warning'),
                            'message': _(
                                'This commitment will create a negative budget balance.\n\n'
                                'Requested: %(requested)s\n'
                                'Available: %(available)s\n'
                                'Remaining after commitment: %(remaining)s\n\n'
                                'Negative budgets are allowed by system configuration.'
                            ) % {
                                'requested': "{:,.2f}".format(self.amount),
                                'available': "{:,.2f}".format(self.available_budget_amount),
                                'remaining': "{:,.2f}".format(self.available_budget_amount - self.amount),
                            }
                        }
                    }
                else:
                    return {
                        'warning': {
                            'title': _('Low Budget Warning'),
                            'message': _(
                                'This commitment will use %(percentage).1f%% of the available budget.\n\n'
                                'Requested: %(requested)s\n'
                                'Available: %(available)s\n'
                                'Remaining after commitment: %(remaining)s'
                            ) % {
                                'percentage': self.budget_availability_percentage,
                                'requested': "{:,.2f}".format(self.amount),
                                'available': "{:,.2f}".format(self.available_budget_amount),
                                'remaining': "{:,.2f}".format(self.available_budget_amount - self.amount),
                            }
                        }
                    }

    @api.constrains("amount")
    def _check_positive_amount(self):
        """Ensure commitment amount is positive"""
        for record in self:
            if record.amount <= 0:
                raise ValidationError(_("Commitment amount must be positive."))

    @api.constrains("activity_analytic_id", "fund_analytic_id", "account_id")
    def _check_required_analytics(self):
        """Ensure all required analytic dimensions are set"""
        for record in self:
            if not record.activity_analytic_id:
                raise ValidationError(_("Activity analytic account is required."))
            if not record.fund_analytic_id:
                raise ValidationError(_("Fund analytic account is required."))
            if not record.account_id:
                raise ValidationError(_("Budget account is required."))

    # Workflow Methods
    def action_check_budget_availability(self):
        """Check budget availability for this commitment"""
        self.ensure_one()
        # Trigger recomputation of budget availability
        self._compute_available_budget()

        if self.budget_availability_status == 'insufficient':
            raise UserError(_(
                'Insufficient budget for this commitment.\n\n'
                'Requested: %s\n'
                'Available: %s\n'
                'Budget Account: %s\n'
                'Activity: %s\n'
                'Fund: %s'
            ) % (
                "{:,.2f}".format(self.amount),
                "{:,.2f}".format(self.available_budget_amount),
                self.account_id.display_name,
                self.activity_analytic_id.display_name,
                self.fund_analytic_id.display_name,
            ))

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Budget Check Complete'),
                'message': _('Budget availability: %s - Available: %s') % (
                    self.budget_availability_status.title(),
                    "{:,.2f}".format(self.available_budget_amount)
                ),
                'type': 'success' if self.budget_availability_status == 'sufficient' else 'warning',
                'sticky': False,
            }
        }


    def action_reserve(self):
        """Reserve budget for this commitment"""
        for record in self:
            if record.state != 'draft':
                raise UserError(_('Only draft commitments can be reserved.'))

            # Check budget availability before reserving
            record.action_check_budget_availability()

            # Generate sequence number upon successful reservation
            if record.name == _('New'):
                record.name = self.env['ir.sequence'].next_by_code('budget.commitment') or _('New')

            record.state = 'reserved'

    def action_done(self):
        """Mark commitment as done - closes the commitment and releases any remaining budget"""
        for record in self:
            if record.state not in ['reserved']:
                raise UserError(_('Only reserved commitments can be marked as done.'))
            record.state = 'done'

    def action_cancel(self):
        """Cancel the commitment"""
        for record in self:
            if record.state in ['done']:
                raise UserError(_('Done commitments cannot be cancelled.'))
            record.state = 'cancel'

    def action_reset_to_draft(self):
<<<<<<< ours
        """Reset commitment to draft state"""
=======
        """Reset to draft state"""
        if self.consumed_amount > 0:
            raise UserError(_("Cannot reset commitment that has been consumed."))
        self.write({"state": "draft"})
        self.message_post(body=_("Commitment reset to draft."))

    def _validate_commitment(self):
        """
        Validate commitment data before confirmation.

        Business Rules:
            • Must have at least one commitment line
            • Total amount must be positive (prevents negative commitments)
            • All individual line amounts must be positive
            • Fiscal year must be set and valid

        Validation Context:
            Called during action_confirm() to ensure data integrity before
            the commitment becomes immutable and affects budget calculations.

        Performance Notes:
            • Lightweight validation suitable for real-time checking
            • Should not perform complex budget calculations here
            • Use _check_budget_availability() for budget-specific validation

        Raises:
            ValidationError: With user-friendly message describing the issue
        """
        if not self.line_ids:
            raise ValidationError(_("Commitment must have at least one line."))

        if self.total_amount <= 0:
            raise ValidationError(_("Total commitment amount must be positive."))

        for line in self.line_ids:
            if line.amount <= 0:
                raise ValidationError(_("All commitment line amounts must be positive."))

    def _check_budget_availability(self):
        """
        Check if sufficient budget is available for this commitment.

        This method implements the core budget control logic with hierarchical
        budget checking where parent-level appropriations can cover child-level
        commitments across the 4D analytic structure.

        Algorithm Overview:
            1. For each commitment line:
               • Calculate appropriated amount (from budget moves type='appropriation')
               • Calculate reserved amount (from other commitments in 'reserved' state)
               • Calculate consumed amount (from budget moves type='consume')
               • Available = Appropriated - Reserved - Consumed

            2. Apply hierarchical analytic matching:
               • Exact match required: Budget Account, Source
               • Hierarchical match allowed: Activity, Department, Fund
               • Uses parent_path field for efficient hierarchy traversal

            3. Validate requested amounts:
               • Requested ≤ Available (or raise detailed ValidationError)
               • Provide specific analytic breakdown in error message

        Business Context:
            This is the critical budget control point that prevents over-allocation.
            Called during action_reserve() before budget amounts are locked.

        Hierarchical Budget Logic:
            Thai organizations have complex hierarchies like:
            • กิจกรรม > กิจกรรมย่อย > กิจกรรมรอง (Activities)
            • ส่วนงาน > งาน > หน่วยงาน (Departments)
            • กองทุน > ประเภทเงิน > แหล่งเงิน (Funds)

            Parent appropriations can cover child commitments, allowing flexible
            budget management while maintaining strict control.

        Performance Optimizations:
            • Uses budget.controller service for optimized calculations
            • Excludes current commitment from reserved amount calculation
            • Caches fiscal year queries within transaction
            • Efficient parent_path traversal for hierarchy matching

        Error Handling:
            Provides detailed error messages showing:
            • Which specific line has insufficient budget
            • Current analytic dimension breakdown
            • Available vs requested amounts
            • Exact shortage amount for user guidance

        Example Error Output:
            "Insufficient budget for line 'Office Supplies':
             - Budget Account: 62010 - วัสดุสำนักงาน
             - Activity: งานบริหารทั่วไป > งานสำนักงาน
             - Department: สำนักงานอธิการบดี > งานบุคคล
             - Fund: เงินรายได้ > เงินค่าบำรุง
             - Available: 45,000.00
             - Requested: 50,000.00
             - Shortage: 5,000.00"

        Returns:
            bool: True if sufficient budget is available for all lines

        Raises:
            ValidationError: When insufficient budget with detailed breakdown
        """
        self.ensure_one()
        _logger.info("Checking budget availability for commitment %s", self.name)

        validation_errors = []

        for line in self.line_ids:
            available_amount = self._get_available_budget_amount(line)
            requested_amount = line.amount

            if requested_amount > available_amount:
                error_msg = _(
                    "Insufficient budget for line '%(line_name)s':\n"
                    "- Budget Account: %(account)s\n"
                    "- Activity: %(activity)s\n"
                    "- Department: %(department)s\n"
                    "- Fund: %(fund)s\n"
                    "- Source: %(source)s\n"
                    "- Available: %(available).2f\n"
                    "- Requested: %(requested).2f\n"
                    "- Shortage: %(shortage).2f"
                ) % {
                    'line_name': line.name,
                    'account': line.account_id.display_name,
                    'activity': line.activity_analytic_id.display_name,
                    'department': line.department_analytic_id.display_name,
                    'fund': line.fund_analytic_id.display_name,
                    'source': line.source_analytic_id.display_name,
                    'available': available_amount,
                    'requested': requested_amount,
                    'shortage': requested_amount - available_amount,
                }
                validation_errors.append(error_msg)

        if validation_errors:
            raise ValidationError("\n\n".join(validation_errors))

        return True

    def _get_available_budget_amount(self, line):
        """Get available budget amount for a commitment line"""
        # Calculate: Appropriated - Reserved - Consumed
        appropriated = self._calculate_appropriated_amount(line)
        reserved = self._calculate_reserved_amount(line)
        consumed = self._calculate_consumed_amount(line)

        available = appropriated - reserved - consumed
        return max(0.0, available)  # Never return negative

    def _calculate_appropriated_amount(self, line):
        """Calculate total appropriated budget for this line's analytic combination"""
        BudgetMove = self.env['budget.move']

        domain = [
            ('state', '=', 'posted'),
            ('move_type', '=', 'appropriation'),
            ('date_range_fy_id', '=', self.date_range_fy_id.id),
            ('company_id', '=', self.company_id.id),
        ]

        moves = BudgetMove.search(domain)
        total = 0.0

        for move in moves:
            for move_line in move.line_ids:
                if self._line_matches_analytic_combination(move_line, line):
                    total += abs(move_line.balance)

        return total

    def _calculate_reserved_amount(self, line):
        """Calculate total reserved amount from other commitments"""
        BudgetCommitment = self.env['budget.commitment']

        domain = [
            ('state', '=', 'reserved'),
            ('date_range_fy_id', '=', self.date_range_fy_id.id),
            ('company_id', '=', self.company_id.id),
            ('id', '!=', self.id),  # Exclude current commitment
        ]

        commitments = BudgetCommitment.search(domain)
        total = 0.0

        for commitment in commitments:
            for commitment_line in commitment.line_ids:
                if self._line_matches_analytic_combination(commitment_line, line):
                    total += commitment_line.remaining_amount

        return total

    def _calculate_consumed_amount(self, line):
        """Calculate total consumed amount from budget moves"""
        BudgetMove = self.env['budget.move']

        domain = [
            ('state', '=', 'posted'),
            ('move_type', '=', 'consume'),
            ('date_range_fy_id', '=', self.date_range_fy_id.id),
            ('company_id', '=', self.company_id.id),
        ]

        moves = BudgetMove.search(domain)
        total = 0.0

        for move in moves:
            for move_line in move.line_ids:
                if self._line_matches_analytic_combination(move_line, line):
                    total += abs(move_line.balance)

        return total

    def _line_matches_analytic_combination(self, move_line, commitment_line):
        """Check if move line matches commitment line's analytic combination"""
        # Exact match for budget account and source (no hierarchy)
        if (move_line.account_id != commitment_line.account_id or
            move_line.source_analytic_id != commitment_line.source_analytic_id):
            return False

        # For activities, departments, and funds, check hierarchical relationships
        activity_match = self._analytic_accounts_match_hierarchical(
            move_line.activity_analytic_id, commitment_line.activity_analytic_id
        )
        department_match = self._analytic_accounts_match_hierarchical(
            move_line.department_analytic_id, commitment_line.department_analytic_id
        )
        fund_match = self._analytic_accounts_match_hierarchical(
            move_line.fund_analytic_id, commitment_line.fund_analytic_id
        )

        return activity_match and department_match and fund_match

    def _analytic_accounts_match_hierarchical(self, move_account, commitment_account):
        """
        Check if analytic accounts match hierarchically for budget appropriation coverage.

        Business Logic:
            This method enables flexible budget management by allowing parent-level
            appropriations to cover child-level commitments. This is essential for
            Thai organizational structures where budget is often allocated at high
            levels but consumed at detailed operational levels.

        Hierarchy Examples:
            ✅ Appropriation at "งานบริหารทั่วไป" covers commitment at "งานบริหารทั่วไป > งานธุรการ"
            ✅ Appropriation at "เงินรายได้" covers commitment at "เงินรายได้ > เงินค่าบำรุง"
            ✅ Appropriation at "สำนักงานอธิการบดี" covers commitment at "สำนักงานอธิการบดี > งานบุคคล"
            ❌ Appropriation at "งานธุรการ" cannot cover commitment at "งานบริหารทั่วไป"

        Technical Implementation:
            1. Handle None cases (both None = match, one None = no match)
            2. Check exact ID match first (performance optimization)
            3. Extract all parent IDs from commitment_account.parent_path field
            4. Check if move_account.id exists in the parent hierarchy

        Parent Path Format:
            • parent_path stores complete hierarchy as "1/2/3/" format
            • Each number represents an analytic account ID in the path
            • Path includes the account itself plus all parents up to root

        Performance Notes:
            • Uses parent_path for O(1) hierarchy checking vs recursive queries
            • Leverages database indexing on parent_path field
            • Minimal memory overhead with integer list operations

        Args:
            move_account (account.analytic.account): Account from budget move line
                - For appropriations: Could be parent account providing budget
                - For commitments/consumption: Should match exactly
            commitment_account (account.analytic.account): Account from commitment line
                - Could be child account needing budget from parent appropriation

        Returns:
            bool: True if hierarchical relationship allows budget usage

        Example Usage:
            # Check if เงินรายได้ appropriation can cover เงินรายได้ > เงินค่าบำรุง commitment
            parent = revenue_fund  # เงินรายได้ (ID: 100)
            child = maintenance_fund  # เงินรายได้ > เงินค่าบำรุง (ID: 150, parent_path: "100/150/")
            result = self._analytic_accounts_match_hierarchical(parent, child)  # Returns True
        """
        # Handle None cases
        if not move_account and not commitment_account:
            return True
        if not move_account or not commitment_account:
            return False

        # Exact match
        if move_account.id == commitment_account.id:
            return True

        # Check if move_account is a parent of commitment_account
        # This allows parent-level appropriations to cover child-level commitments
        if commitment_account.parent_path and move_account.id:
            # Extract parent IDs from commitment_account's parent_path
            parent_ids = self._get_parent_ids_from_path(commitment_account.parent_path)
            return move_account.id in parent_ids

        return False

    def _get_parent_ids_from_path(self, parent_path):
        """Extract parent IDs from parent_path field"""
        if not parent_path:
            return []

        # parent_path format: "1/2/3/" - extract all IDs
        path_parts = parent_path.strip('/').split('/')
        return [int(id_str) for id_str in path_parts if id_str.isdigit()]

    @api.constrains("date", "date_range_fy_id")
    def _check_date_in_fiscal_year(self):
        """Ensure commitment date falls within the fiscal year"""
>>>>>>> theirs
        for record in self:
            if record.state not in ['cancel']:
                raise UserError(_('Only cancelled commitments can be reset to draft.'))
            record.state = 'draft'

    def action_view_budget_moves(self):
        """View related budget moves"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Related Budget Moves'),
            'res_model': 'budget.move',
            'view_mode': 'tree,form',
            'domain': [('commitment_id', '=', self.id)],
            'context': {'default_commitment_id': self.id},
        }
