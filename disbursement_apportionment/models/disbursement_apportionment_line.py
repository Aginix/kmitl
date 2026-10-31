# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class DisbursementApportionmentLine(models.Model):
    """One destination of a request's apportionment (ปันส่วน, ADR-0009): the
    budget code and dimensions the apportioned share is transferred to. Its
    แหล่งเงิน is always the request's — a transfer never crosses sources — so
    only ส่วนงาน, กองทุน and กิจกรรม are kept in its distribution."""

    _name = "disbursement.apportionment.line"
    _inherit = "analytic.mixin"
    _description = "Disbursement Apportionment Line"
    _order = "sequence, id"

    request_id = fields.Many2one(
        "disbursement.request",
        string="Disbursement Request",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sequence = fields.Integer(default=10)
    name = fields.Char(string="Description")
    budget_account_id = fields.Many2one(
        "budget.account",
        string="Budget Account",
        domain=[("budgetable", "=", True), ("budget_type", "=", "expense")],
        required=True,
        ondelete="restrict",
    )
    source_analytic_id = fields.Many2one(
        related="request_id.source_analytic_id",
        string="Source",
    )
    department_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="Department",
        compute="_compute_analytic_id",
        inverse="_inverse_department_analytic",
        domain=[("root_plan_id.code", "=", "departments")],
        store=False,
    )
    fund_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="Fund",
        compute="_compute_analytic_id",
        inverse="_inverse_fund_analytic",
        domain=[("root_plan_id.code", "=", "funds")],
        store=False,
    )
    activity_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="Activity",
        compute="_compute_analytic_id",
        inverse="_inverse_activity_analytic",
        domain=[("root_plan_id.code", "=", "activities")],
        store=False,
    )
    amount = fields.Monetary(required=True)
    currency_id = fields.Many2one(related="request_id.currency_id")

    _analytic_keys = {
        "activities": "activity_analytic_id",
        "departments": "department_analytic_id",
        "funds": "fund_analytic_id",
    }

    @api.constrains("amount")
    def _check_amount(self):
        if self.filtered(lambda line: line.amount <= 0):
            raise ValidationError(_("An apportioned amount must be positive."))

    # Also onchange handlers, as on the request: the form sends the hidden
    # analytic_distribution on save, so it must already hold the dimensions.
    @api.onchange("department_analytic_id")
    def _inverse_department_analytic(self):
        for line in self:
            line._update_analytic_distribution("departments")

    @api.onchange("fund_analytic_id")
    def _inverse_fund_analytic(self):
        for line in self:
            line._update_analytic_distribution("funds")

    @api.onchange("activity_analytic_id")
    def _inverse_activity_analytic(self):
        for line in self:
            line._update_analytic_distribution("activities")

    @api.depends("analytic_distribution")
    def _compute_analytic_id(self):
        for line in self:
            for field_name in self._analytic_keys.values():
                line[field_name] = False
        return super()._compute_analytic_id()

    def _transfer_distribution(self):
        """The destination coordinate: this line's dimensions plus the
        request's แหล่งเงิน."""
        self.ensure_one()
        distribution = dict(self.analytic_distribution or {})
        source = self.request_id.source_analytic_id
        if source:
            distribution[str(source.id)] = 100.0
        return distribution
