from odoo import models


class BudgetTransfer(models.Model):
    """Bridge: a transfer line on a project (``is_project``) budget code must match
    its ``kmitl.project`` source.

    A project budget code does not stand on its own — its budget lives inside a
    specific ``kmitl.project`` that pins the budget code, the fiscal year and the
    four core accounting dimensions the budget was reserved against. Any project
    line on the transfer must agree with that project on all of them.

    The check is written out field-by-field on purpose (the procurement-plan
    bridge mirrors it) so the whole rule reads top-to-bottom in one place.
    """

    _inherit = "budget.transfer"

    def budget_transfer_check_kmitl_project_source(self):
        # base.exception (by_method): return the transfers that FAIL the rule.
        return self.filtered(lambda t: t._kmitl_project_source_mismatch())

    def _kmitl_project_source_mismatch(self):
        """True as soon as any project line disagrees with its source project."""
        self.ensure_one()
        for line in self.line_ids.filtered("transfer_direction"):
            if not line.account_is_project:
                continue  # only project budget codes are governed by this rule

            tag = line.kmitl_project_analytic_id
            if not tag:
                continue  # project code without its project dimension tag

            project = self.env["kmitl.project"].search(
                [("analytic_account_id", "=", tag.id)], limit=1
            )
            if not project:
                return True  # no project matches the line's project tag

            # รหัสงบประมาณ
            if project.budget_account_id != line.account_id:
                return True
            # ปีงบประมาณ (header-owned on the transfer)
            if project.account_fiscal_year_id != self.account_fiscal_year_id:
                return True
            # ส่วนงาน / แหล่งเงิน / กิจกรรม / กองทุน
            if project.department_analytic_id != line.department_analytic_id:
                return True
            if project.source_analytic_id != line.source_analytic_id:
                return True
            if project.activity_analytic_id != line.activity_analytic_id:
                return True
            if project.fund_analytic_id != line.fund_analytic_id:
                return True
        return False
