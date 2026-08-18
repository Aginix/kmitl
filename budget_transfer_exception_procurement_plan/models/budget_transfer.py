from odoo import models


class BudgetTransfer(models.Model):
    """Bridge: a transfer line on a procurement-plan budget code must match its
    ``procurement.plan`` source.

    A procurement-plan budget code does not stand on its own — its budget lives
    inside a specific ``procurement.plan`` that pins the budget code, the fiscal
    year and the four core accounting dimensions the budget was reserved against.
    Any procurement-plan line on the transfer must agree with that plan on all of
    them.

    The check is written out field-by-field on purpose (the kmitl-project bridge
    mirrors it) so the whole rule reads top-to-bottom in one place.
    """

    _inherit = "budget.transfer"

    def budget_transfer_check_procurement_plan_source(self):
        # base.exception (by_method): return the transfers that FAIL the rule.
        return self.filtered(lambda t: t._procurement_plan_source_mismatch())

    def _procurement_plan_source_mismatch(self):
        """True as soon as any plan line disagrees with its source plan."""
        self.ensure_one()
        for line in self.line_ids.filtered("transfer_direction"):
            if not line.account_is_procurement:
                continue  # only procurement-plan budget codes are governed here

            tag = line.procurement_plan_analytic_id
            if not tag:
                return True  # plan code without its procurement-plan tag

            plan = self.env["procurement.plan"].search(
                [("analytic_account_id", "=", tag.id)], limit=1
            )
            if not plan:
                continue  # no plan matches the line's procurement-plan tag

            # รหัสงบประมาณ
            if plan.budget_account_id != line.account_id:
                return True
            # ปีงบประมาณ (header-owned on the transfer)
            if plan.account_fiscal_year_id != self.account_fiscal_year_id:
                return True
            # ส่วนงาน / แหล่งเงิน / กิจกรรม / กองทุน
            if plan.department_analytic_id != line.department_analytic_id:
                return True
            if plan.source_analytic_id != line.source_analytic_id:
                return True
            if plan.activity_analytic_id != line.activity_analytic_id:
                return True
            if plan.fund_analytic_id != line.fund_analytic_id:
                return True
        return False
