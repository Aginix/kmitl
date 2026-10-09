from odoo import models


class BudgetMoveLine(models.Model):
    _inherit = "budget.move.line"

    def _get_pool_owner_commitment(self):
        """The reservations of the project a ``kmitl_project`` tag names."""
        commitments = super()._get_pool_owner_commitment()
        if self.kmitl_project_analytic_id:
            projects = (
                self.env["kmitl.project"]
                .sudo()
                .search([("analytic_account_id", "=", self.kmitl_project_analytic_id.id)])
            )
            commitments |= projects.budget_commitment_ids
        return commitments
