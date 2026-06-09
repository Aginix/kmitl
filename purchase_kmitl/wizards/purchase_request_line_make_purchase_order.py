# -*- coding: utf-8 -*-
from odoo import api, models


class PurchaseRequestLineMakePurchaseOrder(models.TransientModel):
    _inherit = "purchase.request.line.make.purchase.order"

    @api.model
    def _prepare_purchase_order(self, picking_type, group_id, company, origin):
        vals = super()._prepare_purchase_order(picking_type, group_id, company, origin)
        vals.update(
            {
                "department_id": self.item_ids.request_id.department_id.id,
            }
        )
        return vals
