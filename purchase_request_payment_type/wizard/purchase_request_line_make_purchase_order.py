import logging
from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import get_lang

_logger = logging.getLogger(__name__)


class PurchaseRequestLineMakePurchaseOrder(models.TransientModel):
    _inherit = "purchase.request.line.make.purchase.order"

    @api.model
    def _prepare_purchase_order(self, picking_type, group_id, company, origin):
        vals = super()._prepare_purchase_order(picking_type, group_id, company, origin)
        vals.update({
            "payment_type": self.item_ids.request_id.payment_type,
        })
        return vals
