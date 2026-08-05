from odoo import api, fields, models


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    procurement_mode = fields.Selection(
        [
            ("by_officer", "ให้พัสดุจัดหา"),
            ("by_requester", "ผู้ขอระบุเอง"),
        ],
        string="โหมดจัดหา",
        default="by_requester",
        required=True,
        tracking=True,
    )

    @api.onchange("procurement_mode")
    def _onchange_procurement_mode(self):
        if self.procurement_mode == "by_officer":
            self.partner_id = False
