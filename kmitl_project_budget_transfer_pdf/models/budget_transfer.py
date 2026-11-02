from collections import defaultdict

from odoo import models

_SIDES = (("ปรับลด (โอนออก)", "from_line_ids"), ("ปรับเพิ่ม (โอนเข้า)", "to_line_ids"))


class BudgetTransfer(models.Model):
    _inherit = "budget.transfer"

    def _annex_projects(self):
        """งปม.303 enclosure rows: ``[(side label, [(project, amount)])]`` for each
        side that carries project-tagged lines, one row per project (amounts summed)."""
        self.ensure_one()
        Project = self.env["kmitl.project"].sudo().with_context(active_test=False)
        result = []
        for label, field in _SIDES:
            totals = defaultdict(float)
            for line in self[field].filtered("kmitl_project_analytic_id"):
                totals[line.kmitl_project_analytic_id.id] += line.amount
            projects = Project.search([("analytic_account_id", "in", list(totals))])
            if projects:
                projects = projects.sorted(lambda p: p.key or "")
                rows = [(p, totals[p.analytic_account_id.id]) for p in projects]
                result.append((label, rows))
        return result
