from odoo import api, fields, models


class DisbursementRequest(models.Model):
    """A disbursement request charged to a procurement-plan (investment) budget
    account behaves like a budget-account expense: the line product is the budget
    account's own product (hidden from the user, stamped automatically), and the
    procurement-plan dimension is mandatory. The two "must be configured" checks
    are blocking base.exceptions (see data/exception_rule_data.xml), so they
    surface a clear message on submit instead of a raw ORM error."""

    _inherit = "disbursement.request"

    # True when this DR draws an investment budget code. Lives on the request so
    # the line list can hide the whole product column with ``column_invisible``.
    is_procurement_plan_expense = fields.Boolean(
        related="budget_account_id.procurement_plan",
        string="Is Procurement Plan Expense",
    )
    # Mirror the procurement_plan dimension carried in analytic_distribution into
    # a convenience field so the form can require it and the exception rule can
    # test it. The JSON distribution stays the source of truth.
    procurement_plan_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="แผนจัดซื้อจัดจ้าง (มิติ)",
        compute="_compute_procurement_plan_analytic_id",
        inverse="_inverse_procurement_plan_analytic",
        domain=[("root_plan_id.code", "=", "procurement_plan")],
        store=False,
    )

    @api.depends("analytic_distribution")
    def _compute_procurement_plan_analytic_id(self):
        for rec in self:
            account_ids = [int(a) for a in rec.analytic_distribution or {}]
            accounts = self.env["account.analytic.account"].browse(account_ids)
            rec.procurement_plan_analytic_id = accounts.filtered(
                lambda a: a.root_plan_id.code == "procurement_plan"
            )[:1]

    def _inverse_procurement_plan_analytic(self):
        for rec in self:
            rec._update_analytic_distribution("procurement_plan")

    # For procurement-plan expenses the line product is not chosen by hand — it
    # is the product bound to the budget account (budget_product). Stamp it on any
    # change; a code with no bound product leaves the line blank and is refused on
    # submit by the excep_disbursement_procurement_no_product rule.
    @api.onchange("budget_account_id", "line_ids")
    def _onchange_fill_procurement_plan_product(self):
        for rec in self.filtered("is_procurement_plan_expense"):
            product = rec.budget_account_id.product_id
            if not product:
                continue
            lines = rec.line_ids.filtered(lambda l: l.product_id != product)
            if lines:
                lines.product_id = product.id
