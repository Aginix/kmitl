# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    _state_from = ["submitted"]
    _state_to = ["posted"]

    def action_submit(self):
        """Override submit to auto-trigger tier validation."""
        # Call parent to move to submitted state
        res = super().action_submit()

        # Auto-trigger tier validation if needed
        for move in self:
            if move.need_validation and move.state == "submitted":
                move.request_validation()

        return res
