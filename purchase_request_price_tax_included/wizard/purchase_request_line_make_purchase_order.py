from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import get_lang


class PurchaseRequestLineMakePurchaseOrder(models.TransientModel):
    _inherit = "purchase.request.line.make.purchase.order"

    @api.model
    def _prepare_purchase_order_line(self, po, item):
        res = super()._prepare_purchase_order_line(po, item)
        res['taxes_id'] = [(4, item.tax_id.id)]
        return res
