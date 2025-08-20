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
        draft → confirmed → reserved → consumed → done
        │        │          │         │         │
        │        │          │         │         └── Fully processed, no more changes
        │        │          │         └─────────── Budget consumed via budget moves
        │        │          └───────────────────── Budget reserved, prevents over-commitment
        │        └──────────────────────────────── Validated, ready for reservation
        └───────────────────────────────────────── Editable, no budget impact

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
        "confirmed": [("readonly", True)],
        "reserved": [("readonly", True)],
        "consumed": [("readonly", True)],
        "done": [("readonly", True)],
        "cancel": [("readonly", True)],
    }

    # Header fields (from original budget.commitment)
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
            ("confirmed", "Confirmed"),
            ("reserved", "Reserved"),
            ("consumed", "Consumed"),
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
        string="Fiscal Year",
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

    # Line fields (from original budget.commitment.line)
    sequence = fields.Integer(
        string="Sequence",
        default=10,
        help="Sequence for ordering lines",
    )

    account_id = fields.Many2one(
        comodel_name="budget.account",
        string="Budget Account",
        required=True,
        index=True,
        tracking=True,
        domain="[('budgetable', '=', True), ('budget_type', '=', 'expense')]",
    )

    line_name = fields.Char(
        string="Line Description",
        related="account_id.name",
        store=True,
        tracking=True,
    )

    amount = fields.Monetary(
        string="Committed Amount",
        required=True,
        currency_field="currency_id",
        tracking=True,
        help="Amount to be committed for this budget line",
    )

    # 4-Dimensional Analytic Distribution
    activity_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="กิจกรรม",
        required=True,
        tracking=True,
        domain=[("root_plan_id.code", "=", "activities")],
        help="Activity dimension - แผนงาน/กิจกรรม",
    )

    department_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="ส่วนงาน",
        required=True,
        tracking=True,
        domain=[("root_plan_id.code", "=", "departments")],
        help="Department dimension",
    )

    fund_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="กองทุน",
        required=True,
        tracking=True,
        domain=[("root_plan_id.code", "=", "funds")],
        help="Fund dimension - กองทุน",
    )

    source_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="แหล่งเงิน",
        required=True,
        tracking=True,
        domain=[("root_plan_id.code", "=", "sources")],
        help="Source dimension",
    )

    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
        tracking=True,
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
        help="Budget availability status for this commitment",
    )

    budget_availability_percentage = fields.Float(
        string="% of Available",
        compute="_compute_available_budget",
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

    def action_confirm(self):
        """Confirm the commitment"""
        for record in self:
            if record.state != 'draft':
                raise UserError(_('Only draft commitments can be confirmed.'))
            record.state = 'confirmed'

    def action_reserve(self):
        """Reserve budget for this commitment"""
        for record in self:
            if record.state != 'confirmed':
                raise UserError(_('Only confirmed commitments can be reserved.'))
            
            # Check budget availability before reserving
            record.action_check_budget_availability()
            record.state = 'reserved'

    def action_done(self):
        """Mark commitment as done"""
        for record in self:
            if record.state not in ['consumed']:
                raise UserError(_('Only consumed commitments can be marked as done.'))
            record.state = 'done'

    def action_cancel(self):
        """Cancel the commitment"""
        for record in self:
            if record.state in ['done']:
                raise UserError(_('Done commitments cannot be cancelled.'))
            record.state = 'cancel'

    def action_reset_to_draft(self):
        """Reset commitment to draft state"""
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