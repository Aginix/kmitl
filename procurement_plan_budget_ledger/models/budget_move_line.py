from odoo import models


class BudgetMoveLine(models.Model):
    _inherit = "budget.move.line"

    def _get_pool_owner_commitment(self):
        """The reservations of the plan a ``procurement_plan`` tag names."""
        commitments = super()._get_pool_owner_commitment()
        if self.procurement_plan_analytic_id:
            plans = (
                self.env["procurement.plan"]
                .sudo()
                .search(
                    [("analytic_account_id", "=", self.procurement_plan_analytic_id.id)]
                )
            )
            commitments |= plans.budget_commitment_ids
        return commitments
