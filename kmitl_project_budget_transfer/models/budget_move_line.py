from odoo import api, fields, models


class BudgetMoveLine(models.Model):
    """Narrow the transfer-line project picker to the projects whose budget code,
    fiscal year and dimensions match what the line already carries.

    Progressive: a dimension still blank on the line does not filter. The
    blocking exception rule (``budget_transfer_exception_kmitl_project``) stays
    the final gate at ยืนยัน. Projects are searched as superuser (another unit's
    project records are unreadable); the analytic OU filter then hides other
    units' projects unless they are flagged as supported (ADR-0008).
    """

    _inherit = "budget.move.line"

    allowed_kmitl_project_analytic_ids = fields.Many2many(
        "account.analytic.account",
        compute="_compute_allowed_kmitl_project_analytic_ids",
    )

    @api.depends(
        "account_id",
        "activity_analytic_id",
        "fund_analytic_id",
        "department_analytic_id",
        "source_analytic_id",
        "move_id.account_fiscal_year_id",
    )
    def _compute_allowed_kmitl_project_analytic_ids(self):
        Project = self.env["kmitl.project"].sudo()
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
            if line.department_analytic_id:
                domain.append(
                    ("department_analytic_id", "=", line.department_analytic_id.id)
                )
            projects = Project.search(domain)
            # Non-stored on kmitl.project — filter in Python.
            for dim in (
                "activity_analytic_id",
                "fund_analytic_id",
                "source_analytic_id",
            ):
                if line[dim]:
                    projects = projects.filtered(lambda p, d=dim: p[d] == line[d])
            line.allowed_kmitl_project_analytic_ids = projects.analytic_account_id
