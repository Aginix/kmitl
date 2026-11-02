from collections import defaultdict

from odoo import models

_SIDES = (("ปรับลด (โอนออก)", "from_line_ids"), ("ปรับเพิ่ม (โอนเข้า)", "to_line_ids"))


class BudgetTransfer(models.Model):
    _inherit = "budget.transfer"

    def _annex_procurement_plans(self):
        """งปม.303 enclosure rows: ``[(side label, [(plan, amount)])]`` for each
        side that carries plan-tagged lines, one row per plan (amounts summed)."""
        self.ensure_one()
        Plan = self.env["procurement.plan"].sudo().with_context(active_test=False)
        result = []
        for label, field in _SIDES:
            totals = defaultdict(float)
            for line in self[field].filtered("procurement_plan_analytic_id"):
                totals[line.procurement_plan_analytic_id.id] += line.amount
            plans = Plan.search([("analytic_account_id", "in", list(totals))])
            if plans:
                plans = plans.sorted(lambda p: p.name or "")
                rows = [(p, totals[p.analytic_account_id.id]) for p in plans]
                result.append((label, rows))
        return result
