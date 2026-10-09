from odoo import models


class BudgetMove(models.Model):
    _inherit = "budget.move"

    def _recompute_project_amounts(self):
        """A commitment's event moves only post usage buckets, which never
        change a project's Current Budget (appropriation/entry lines), so they
        skip the project recompute (budget ADR-0016)."""
        return super(
            BudgetMove, self.filtered(lambda m: not m.commitment_id)
        )._recompute_project_amounts()
