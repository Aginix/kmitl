# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, models
from odoo.exceptions import UserError


class ResPartner(models.Model):
    _inherit = "res.partner"

    def unlink(self):
        walkin_id = self.env["kmitl.receipt"]._default_partner_id()
        if walkin_id and walkin_id in self.ids:
            raise UserError(
                _("ไม่สามารถลบลูกค้า Walk-In ได้ เนื่องจากระบบใบเสร็จใช้งานอยู่")
            )
        return super().unlink()
