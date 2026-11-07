from odoo import models


class BudgetCommitment(models.Model):
    _inherit = "budget.commitment"

    def budget_commitment_check_procurement_plan_tag(self):
        # base.exception (by_method): return the commitments that FAIL the rule.
        return self.filtered(
            lambda c: c.account_id.procurement_plan
            and not c.procurement_plan_analytic_id
        )
