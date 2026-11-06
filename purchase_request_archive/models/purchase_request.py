from odoo import _, fields, models
from odoo.exceptions import UserError


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    active = fields.Boolean(default=True, tracking=True, copy=False)

    def action_archive(self):
        """Only finished-dead requests (cancelled / rejected) may be archived."""
        if self.filtered(lambda r: r.state not in ("cancelled", "rejected")):
            raise UserError(
                _("Only cancelled or rejected purchase requests can be archived.")
            )
        return super().action_archive()
