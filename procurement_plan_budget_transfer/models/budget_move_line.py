from odoo import api, fields, models


class BudgetMoveLine(models.Model):
    """Narrow the transfer-line procurement-plan picker to the plans whose budget
    code, fiscal year and dimensions match what the line already carries.

    Progressive: a dimension still blank on the line does not filter. The
    blocking exception rule (``budget_transfer_exception_procurement_plan``)
    stays the final gate at ยืนยัน. Plans are searched as superuser; the analytic
    OU filter still governs what the picker shows.
    """

    _inherit = "budget.move.line"

    allowed_procurement_plan_analytic_ids = fields.Many2many(
        "account.analytic.account",
        compute="_compute_allowed_procurement_plan_analytic_ids",
    )

    @api.depends(
        "account_id",
        "activity_analytic_id",
        "fund_analytic_id",
        "department_analytic_id",
        "source_analytic_id",
        "move_id.account_fiscal_year_id",
    )
    def _compute_allowed_procurement_plan_analytic_ids(self):
        Plan = self.env["procurement.plan"].sudo()
        for line in self:
            domain = [("analytic_account_id", "!=", False)]
            if line.account_id:
                domain.append(("budget_account_id", "=", line.account_id.id))
            if line.move_id.account_fiscal_year_id:
                domain.append(
                    (
                        "account_fiscal_year_id",
                        "=",
                        line.move_id.account_fiscal_year_id.id,
                    )
                )
            for dim in (
                "department_analytic_id",
                "activity_analytic_id",
                "source_analytic_id",
            ):
                if line[dim]:
                    domain.append((dim, "=", line[dim].id))
            plans = Plan.search(domain)
            # Non-stored on procurement.plan — filter in Python.
            if line.fund_analytic_id:
                plans = plans.filtered(
                    lambda p: p.fund_analytic_id == line.fund_analytic_id
                )
            line.allowed_procurement_plan_analytic_ids = plans.analytic_account_id
