from odoo import models


class BudgetCommitmentMixin(models.AbstractModel):
    _inherit = "budget.commitment.mixin"

    def action_view_budget_dashboard(self):
        """Open ตรวจสอบงบประมาณ in a floating window instead of a dialog, so
        the form stays editable beside it."""
        action = super().action_view_budget_dashboard()
        return dict(action, tag="agx_floating_window", params={"tag": action["tag"]})
