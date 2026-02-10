import logging

from odoo import Command, api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class BudgetCommitmentLine(models.Model):
    """Budget Commitment Line - Ledger entry within budget commitments.

    Each line represents a ledger entry of type 'reserve', 'obligate', or 'consume':
    - reserve: Budget earmark (positive = add, negative = reduce)
    - obligate: Procurement obligation (positive = add, negative = release)
    - consume: Budget consumption (positive amount, posted individually to budget.move)
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
            ("consume", "Consume"),
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
        related="commitment_id.department_analytic_id",
        store=True,
        readonly=True,
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
        related="commitment_id.source_analytic_id",
        store=True,
        readonly=True,
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

    is_posted = fields.Boolean(
        string="Posted",
        default=False,
        readonly=True,
        help="Whether this consume line has been posted to a budget move.",
    )

    budget_move_id = fields.Many2one(
        comodel_name="budget.move",
        string="Posted Budget Move",
        readonly=True,
        ondelete="set null",
        help="Budget move created when this consume line was posted.",
    )

    # === Analytic Computation === #

    @api.depends("analytic_distribution")
    def _compute_analytic_fields(self):
        """Compute activity and fund from distribution JSON.

        Department and source are related fields from the header.
        """
        for line in self:
            line.activity_analytic_id = False
            line.fund_analytic_id = False

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
                        elif code == "funds":
                            line.fund_analytic_id = aa

    def _update_analytic_distribution(self):
        """Update analytic distribution JSON from activity and fund fields."""
        self.ensure_one()
        distribution = {}
        for account in [
            self.activity_analytic_id,
            self.fund_analytic_id,
        ]:
            if account:
                distribution[str(account.id)] = 100.0
        self.analytic_distribution = distribution if distribution else False

    def _inverse_activity_analytic(self):
        for line in self:
            line._update_analytic_distribution()

    def _inverse_fund_analytic(self):
        for line in self:
            line._update_analytic_distribution()

    # === Consume Line Posting === #

    def post_line(self):
        """Post a consume line to create a budget.move."""
        for line in self:
            if line.line_type != "consume":
                raise UserError(_("Only consume lines can be posted."))
            if line.is_posted:
                raise UserError(_("Line is already posted."))
            if line.commitment_id.state != "in_progress":
                raise UserError(
                    _("Commitment must be in progress to post consume lines.")
                )
            budget_move = line._create_budget_move_from_line()
            line.is_posted = True
            line.budget_move_id = budget_move.id
        return True

    def _create_budget_move_from_line(self):
        """Create a budget.move with a single line from this consume line."""
        self.ensure_one()
        move_vals = {
            "name": _("Consumption of %s") % self.commitment_id.name,
            "date": self.date or fields.Date.today(),
            "account_fiscal_year_id": (
                self.commitment_id.account_fiscal_year_id.id
            ),
            "commitment_id": self.commitment_id.id,
            "move_type": "consume",
            "company_id": self.company_id.id,
            "currency_id": self.currency_id.id,
            "department_analytic_id": (
                self.department_analytic_id.id
                if self.department_analytic_id
                else False
            ),
            "source_analytic_id": (
                self.source_analytic_id.id
                if self.source_analytic_id
                else False
            ),
            "line_ids": [
                Command.create(
                    {
                        "account_id": self.account_id.id,
                        "balance": -abs(self.amount),
                        "commitment_line_id": self.id,
                        "activity_analytic_id": (
                            self.activity_analytic_id.id
                            if self.activity_analytic_id
                            else False
                        ),
                        "department_analytic_id": (
                            self.department_analytic_id.id
                            if self.department_analytic_id
                            else False
                        ),
                        "fund_analytic_id": (
                            self.fund_analytic_id.id
                            if self.fund_analytic_id
                            else False
                        ),
                        "source_analytic_id": (
                            self.source_analytic_id.id
                            if self.source_analytic_id
                            else False
                        ),
                    }
                )
            ],
        }
        budget_move = self.env["budget.move"].create(move_vals)
        budget_move.action_post()
        return budget_move
