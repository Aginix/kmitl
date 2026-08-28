# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, models
from odoo.exceptions import UserError


class ResPartner(models.Model):
    _inherit = "res.partner"

    def unlink(self):
        walkin_id = self.env["kmitl.receipt"]._default_partner_id()
        if walkin_id and walkin_id in self.ids:
            raise UserError(
                _("Cannot delete the walk-in customer because it is in use by the receipt system.")
            )
        return super().unlink()
