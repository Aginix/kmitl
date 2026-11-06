from odoo import api, models


class BudgetTransfer(models.Model):
    """กลับรายการ on a posted transfer reverses its delegated move; the
    reversal fields themselves come through ``_inherits`` (budget ADR-0020)."""

    _inherit = "budget.transfer"

    def action_reverse(self):
        self.ensure_one()
        return self.move_id.action_reverse()

    def action_view_reversals(self):
        self.ensure_one()
        return self.move_id.action_view_reversals()

    @api.depends("reversal_move_ids.state")
    def _compute_button_visibility(self):
        """The move's reset is blocked while a reversal is live; hide the
        transfer's posted reset with it."""
        res = super()._compute_button_visibility()
        for transfer in self.filtered(
            lambda t: t.reversal_move_ids.filtered(lambda m: m.state != "cancel")
        ):
            transfer.show_reset_posted_button = False
        return res
