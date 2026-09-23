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

    is_procurement_mode_editable = fields.Boolean(
        compute="_compute_is_procurement_mode_editable",
        readonly=True,
        store=False,
    )

    @api.depends("is_editable")
    def _compute_is_procurement_mode_editable(self):
        for rec in self:
            rec.is_procurement_mode_editable = rec.is_editable

    @api.onchange("procurement_mode")
    def _onchange_procurement_mode(self):
        if self.procurement_mode == "by_officer":
            self.partner_id = False
            self.vat_included = "exclusive"
            self.tax_id = False
