import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class BudgetCommitmentLine(models.Model):
    """Budget Commitment Line - Ledger entry within budget commitments.

    Each line represents a ledger entry of type 'reserve' or 'obligate':
    - reserve: Budget earmark (positive = add, negative = reduce)
    - obligate: Procurement obligation (positive = add, negative = release)

    Consumption is tracked separately via budget.move / budget.move.line.
    """

    _name = "budget.commitment.line"
    _description = "Budget Commitment Line"
    _order = "sequence, id"

    commitment_id = fields.Many2one(
        comodel_name="budget.commitment",
        string="Budget Commitment",
        required=True,
        ondelete="cascade",
        index=True,
    )

    line_type = fields.Selection(
        selection=[
            ("reserve", "Reserve"),
            ("obligate", "Obligate"),
        ],
        string="Line Type",
        required=True,
        default="reserve",
        index=True,
    )

    sequence = fields.Integer(
        string="Sequence",
        default=10,
    )

    date = fields.Date(
        string="Date",
        default=fields.Date.context_today,
    )

    account_id = fields.Many2one(
        comodel_name="budget.account",
        string="รหัสงบประมาณ",
        required=True,
        index=True,
        domain="[('budgetable', '=', True), ('budget_type', '=', 'expense')]",
    )

    amount = fields.Monetary(
        string="จำนวนเงิน",
        required=True,
        currency_field="currency_id",
    )

    description = fields.Char(
        string="Description",
    )

    # === Analytic Distribution === #

    analytic_distribution = fields.Json(
        string="Analytic Distribution",
    )

    activity_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="กิจกรรม",
        compute="_compute_analytic_fields",
        inverse="_inverse_activity_analytic",
        domain=[("root_plan_id.code", "=", "activities")],
    )

    department_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="ส่วนงาน",
        compute="_compute_analytic_fields",
        inverse="_inverse_department_analytic",
        domain=[("root_plan_id.code", "=", "departments")],
    )

    fund_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="กองทุน",
        compute="_compute_analytic_fields",
        inverse="_inverse_fund_analytic",
        domain=[("root_plan_id.code", "=", "funds")],
    )

    source_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="แหล่งเงิน",
        compute="_compute_analytic_fields",
        inverse="_inverse_source_analytic",
        domain=[("root_plan_id.code", "=", "sources")],
    )

    # === Related from parent === #

    currency_id = fields.Many2one(
        related="commitment_id.currency_id",
        store=True,
        readonly=True,
    )

    company_id = fields.Many2one(
        related="commitment_id.company_id",
        store=True,
        readonly=True,
    )

    parent_state = fields.Selection(
        related="commitment_id.state",
        store=True,
        string="Status",
    )

    account_fiscal_year_id = fields.Many2one(
        related="commitment_id.account_fiscal_year_id",
        store=True,
        readonly=True,
    )

    # === Budget Move Tracking === #

    budget_move_line_ids = fields.One2many(
        comodel_name="budget.move.line",
        inverse_name="commitment_line_id",
        string="Related Budget Move Lines",
        readonly=True,
    )

    # === Analytic Computation === #

    @api.depends("analytic_distribution")
    def _compute_analytic_fields(self):
        """Compute 4D analytic fields from distribution JSON."""
        for line in self:
            line.activity_analytic_id = False
            line.department_analytic_id = False
            line.fund_analytic_id = False
            line.source_analytic_id = False

            if line.analytic_distribution:
                analytic_ids = [
                    int(aid)
                    for aid in line.analytic_distribution.keys()
                    if str(aid).isdigit()
                ]
                if analytic_ids:
                    analytics = self.env["account.analytic.account"].browse(
                        analytic_ids
                    )
                    for aa in analytics.exists():
                        code = aa.root_plan_id.code
                        if code == "activities":
                            line.activity_analytic_id = aa
                        elif code == "departments":
                            line.department_analytic_id = aa
                        elif code == "funds":
                            line.fund_analytic_id = aa
                        elif code == "sources":
                            line.source_analytic_id = aa

    def _update_analytic_distribution(self):
        """Update analytic distribution JSON from individual fields."""
        self.ensure_one()
        distribution = {}
        for account in [
            self.activity_analytic_id,
            self.department_analytic_id,
            self.fund_analytic_id,
            self.source_analytic_id,
        ]:
            if account:
                distribution[str(account.id)] = 100.0
        self.analytic_distribution = distribution if distribution else False

    def _inverse_activity_analytic(self):
        for line in self:
            line._update_analytic_distribution()

    def _inverse_department_analytic(self):
        for line in self:
            line._update_analytic_distribution()

    def _inverse_fund_analytic(self):
        for line in self:
            line._update_analytic_distribution()

    def _inverse_source_analytic(self):
        for line in self:
            line._update_analytic_distribution()
