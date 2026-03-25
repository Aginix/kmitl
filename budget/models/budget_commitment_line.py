import logging

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class BudgetCommitmentLine(models.Model):
    """Budget Commitment Line - Ledger entry for budget operations.

    Each line represents a budget transaction:
    - reserve: จองงบประมาณ (positive = จอง, negative = คืนจอง)
    - obligate: ผูกพันงบประมาณ (positive = ผูกพัน, negative = คืนผูกพัน)
    - consume: ตัดงบประมาณ (positive = ตัดงบ, negative = คืนเงิน)
    """

    _name = "budget.commitment.line"
    _description = "Budget Commitment Line"
    _inherit = ["analytic.mixin", "mail.thread"]
    _order = "sequence, id"

    commitment_id = fields.Many2one(
        comodel_name="budget.commitment",
        string="Commitment",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sequence = fields.Integer(default=10)
    date = fields.Date(
        string="Date",
        default=fields.Date.context_today,
        required=True,
    )
    name = fields.Char(string="Description")
    move_type = fields.Selection(
        selection=[
            ("reserve", "จองงบ"),
            ("obligate", "ผูกพัน"),
            ("consume", "ตัดงบ"),
        ],
        string="Type",
        required=True,
        default="reserve",
        tracking=True,
    )
    account_id = fields.Many2one(
        comodel_name="budget.account",
        string="รหัสงบประมาณ",
        required=True,
        index=True,
        domain="[('budgetable', '=', True), ('budget_type', '=', 'expense')]",
    )
    amount = fields.Monetary(
        string="Amount",
        required=True,
        currency_field="currency_id",
        help="Positive = forward (reserve/obligate/consume), Negative = reversal",
    )
    state = fields.Selection(
        selection=[
            ("posted", "Posted"),
            ("cancel", "Cancelled"),
        ],
        string="Status",
        required=True,
        default="posted",
        tracking=True,
    )

    # Analytic convenience fields (line-level: activity + fund only)
    activity_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="กิจกรรม",
        compute="_compute_analytic_id",
        inverse="_inverse_activity_analytic",
        domain=[("root_plan_id.code", "=", "activities")],
        store=False,
    )
    fund_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="กองทุน",
        compute="_compute_analytic_id",
        inverse="_inverse_fund_analytic",
        domain=[("root_plan_id.code", "=", "funds")],
        store=False,
    )

    _analytic_keys = {
        "activities": "activity_analytic_id",
        "funds": "fund_analytic_id",
    }

    def _inverse_activity_analytic(self):
        for line in self:
            line._update_analytic_distribution("activities")

    def _inverse_fund_analytic(self):
        for line in self:
            line._update_analytic_distribution("funds")

    # Related from header
    department_analytic_id = fields.Many2one(
        related="commitment_id.department_analytic_id",
        store=True,
        string="ส่วนงาน",
    )
    source_analytic_id = fields.Many2one(
        related="commitment_id.source_analytic_id",
        store=True,
        string="แหล่งเงิน",
    )
    currency_id = fields.Many2one(related="commitment_id.currency_id")
    company_id = fields.Many2one(
        related="commitment_id.company_id",
        store=True,
    )
    account_fiscal_year_id = fields.Many2one(
        related="commitment_id.account_fiscal_year_id",
        store=True,
        string="ปีงบประมาณ",
    )

    @api.constrains("amount", "move_type", "state")
    def _check_commitment_limits(self):
        """Enforce cascade constraints: reserved <= cap, obligated <= reserved, consumed <= obligated"""
        commitments = self.mapped("commitment_id")
        for commitment in commitments:
            posted = commitment.line_ids.filtered(lambda l: l.state == "posted")
            total_reserved = sum(
                posted.filtered(lambda l: l.move_type == "reserve").mapped("amount")
            )
            total_obligated = sum(
                posted.filtered(lambda l: l.move_type == "obligate").mapped("amount")
            )
            total_consumed = sum(
                posted.filtered(lambda l: l.move_type == "consume").mapped("amount")
            )

            if commitment.amount and total_reserved > commitment.amount:
                raise ValidationError(
                    _(
                        "Total reserved (%(reserved).2f) exceeds commitment cap (%(cap).2f)"
                    )
                    % {"reserved": total_reserved, "cap": commitment.amount}
                )
            if total_obligated > total_reserved:
                raise ValidationError(
                    _(
                        "Total obligated (%(obligated).2f) exceeds total reserved (%(reserved).2f)"
                    )
                    % {"obligated": total_obligated, "reserved": total_reserved}
                )
            if total_consumed > total_obligated:
                raise ValidationError(
                    _(
                        "Total consumed (%(consumed).2f) exceeds total obligated (%(obligated).2f)"
                    )
                    % {"consumed": total_consumed, "obligated": total_obligated}
                )

    def action_cancel(self):
        for line in self:
            if line.state != "cancel":
                line.state = "cancel"

    def action_post(self):
        for line in self:
            if line.state != "posted":
                line.state = "posted"

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        # Auto-advance header state when obligate/consume lines are added
        for line in lines.filtered(
            lambda l: l.state == "posted" and l.move_type in ("obligate", "consume")
        ):
            if line.commitment_id.state == "reserved":
                line.commitment_id.state = "partial"
        return lines
