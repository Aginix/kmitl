import logging
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class BudgetCommitmentLine(models.Model):
    _name = "budget.commitment.line"
    _description = "Budget Commitment Line"
    _inherit = ["analytic.distribution.mixin", "mail.thread"]
    _order = "commitment_id, sequence, id"

    commitment_id = fields.Many2one(
        comodel_name="budget.commitment",
        string="Budget Commitment",
        required=True,
        readonly=True,
        index=True,
        auto_join=True,
        ondelete="cascade",
    )

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

    name = fields.Char(
        string="Description",
        required=True,
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
        compute="_compute_department_analytic",
        store=True,
        readonly=True,
        help="Department from commitment header",
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
        compute="_compute_source_analytic",
        store=True,
        readonly=True,
        help="Source from commitment header",
    )

    # Related fields from parent
    date = fields.Date(
        related="commitment_id.date",
        store=True,
        string="Commitment Date",
    )

    date_range_fy_id = fields.Many2one(
        related="commitment_id.date_range_fy_id",
        store=True,
        string="Fiscal Year",
    )

    parent_state = fields.Selection(
        related="commitment_id.state",
        store=True,
        string="Commitment Status",
    )

    company_id = fields.Many2one(
        related="commitment_id.company_id",
        store=True,
        string="Company",
    )

    currency_id = fields.Many2one(
        related="commitment_id.currency_id",
        store=True,
        string="Currency",
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
        help="Additional notes for this commitment line",
    )

    @api.depends("commitment_id.department_analytic_id")
    def _compute_department_analytic(self):
        """Department comes from the commitment header"""
        for line in self:
            line.department_analytic_id = line.commitment_id.department_analytic_id

    @api.depends("commitment_id.source_analytic_id")
    def _compute_source_analytic(self):
        """Source comes from the commitment header"""
        for line in self:
            line.source_analytic_id = line.commitment_id.source_analytic_id

    @api.depends("amount", "commitment_id.budget_move_ids.line_ids")
    def _compute_consumed_amount(self):
        """Calculate how much of this line has been consumed by budget moves"""
        for line in self:
            consumed = 0.0

            # Find budget move lines that match this commitment line's analytics
            related_moves = line.commitment_id.budget_move_ids.filtered(
                lambda m: m.state == "posted"
            )

            for move in related_moves:
                for move_line in move.line_ids:
                    # Check if budget move line matches this commitment line
                    if (move_line.account_id == line.account_id and
                        move_line.activity_analytic_id == line.activity_analytic_id and
                        move_line.fund_analytic_id == line.fund_analytic_id):
                        consumed += abs(move_line.balance)

            line.consumed_amount = min(consumed, line.amount)

    @api.depends("amount", "consumed_amount")
    def _compute_remaining_amount(self):
        """Calculate remaining amount available"""
        for line in self:
            line.remaining_amount = line.amount - line.consumed_amount

    @api.onchange("account_id")
    def _onchange_account_id(self):
        """Update name when budget account changes"""
        if self.account_id:
            if not self.name:
                self.name = self.account_id.name

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

    @api.constrains("amount")
    def _check_positive_amount(self):
        """Ensure commitment amount is positive"""
        for line in self:
            if line.amount <= 0:
                raise ValidationError(_("Commitment amount must be positive."))

    @api.constrains("activity_analytic_id", "fund_analytic_id", "account_id")
    def _check_required_analytics(self):
        """Ensure all required analytic dimensions are set"""
        for line in self:
            if not line.activity_analytic_id:
                raise ValidationError(_("Activity analytic account is required."))
            if not line.fund_analytic_id:
                raise ValidationError(_("Fund analytic account is required."))
            if not line.account_id:
                raise ValidationError(_("Budget account is required."))

    def name_get(self):
        """Custom name display"""
        result = []
        for line in self:
            name = f"[{line.budget_account_code}] {line.name}"
            if line.amount:
                name += f" - {line.currency_id.symbol}{line.amount:,.2f}"
            result.append((line.id, name))
        return result

    @api.model
    def get_analytic_distribution(self):
        """Build analytic distribution dictionary for integration"""
        distribution = {}

        if self.activity_analytic_id:
            distribution[str(self.activity_analytic_id.id)] = 100.0
        if self.department_analytic_id:
            distribution[str(self.department_analytic_id.id)] = 100.0
        if self.fund_analytic_id:
            distribution[str(self.fund_analytic_id.id)] = 100.0
        if self.source_analytic_id:
            distribution[str(self.source_analytic_id.id)] = 100.0

        return distribution

    def create_budget_move_line(self, move_id, amount):
        """Helper method to create budget move line from commitment line"""
        self.ensure_one()

        budget_move_line_vals = {
            'move_id': move_id,
            'account_id': self.account_id.id,
            'name': self.name,
            'balance': amount,
            'activity_analytic_id': self.activity_analytic_id.id,
            'department_analytic_id': self.department_analytic_id.id,
            'fund_analytic_id': self.fund_analytic_id.id,
            'source_analytic_id': self.source_analytic_id.id,
            'notes': f"From commitment: {self.commitment_id.name}",
        }

        return self.env['budget.move.line'].create(budget_move_line_vals)
