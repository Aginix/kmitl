# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, models


class DisbursementRequest(models.Model):
    _inherit = "disbursement.request"

    def action_open_attachment_carousel(self):
        self.ensure_one()
        return {
            "type": "ir.actions.client",
            "tag": "disbursement_attachment_carousel",
            "target": "new",
            "name": _("ไฟล์แนบทั้งหมด — %s") % (self.name or ""),
            # dialog_size is read by ActionDialog to pick a modal width class
            "context": {"dialog_size": "extra-large"},
            "params": {"res_id": self.id, "name": self.name or ""},
        }
