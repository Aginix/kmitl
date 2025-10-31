# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models, api


class AccountMove(models.Model):
    _inherit = "account.move"

    _state_from = ["submitted"]
    _state_to = ["posted"]

    @api.depends("date", "auto_post", "state", "validation_status")
    def _compute_hide_post_button(self):
        """Override to show Post button for submitted state."""
        super()._compute_hide_post_button()
        for move in self:
            if move.validation_status == "validated" and move.state == "submitted":
                move.hide_post_button = False
            else:
                move.hide_post_button = True

    def action_submit(self):
        """Override submit to auto-trigger tier validation."""
        # Call parent to move to submitted state
        res = super().action_submit()

        # Auto-trigger tier validation if needed
        for move in self:
            if move.need_validation and move.state == "submitted":
                move.request_validation()

        return res
