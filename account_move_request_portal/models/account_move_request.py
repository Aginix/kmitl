# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import models


class AccountMoveRequest(models.Model):
    _name = "account.move.request"
    _inherit = ["account.move.request", "portal.mixin"]

    def _compute_access_url(self):
        """Compute the portal URL for the account move request."""
        super()._compute_access_url()
        for request in self:
            request.access_url = f"/my/account_move_request/{request.id}"

    def _get_report_base_filename(self):
        """Return the base filename for the report."""
        self.ensure_one()
        return f"Account Move Request-{self.name}"

    def open_preview(self):
        """Open preview in portal."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "target": "new",
            "url": self.get_portal_url(),
        }
