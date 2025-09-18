# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class PurchaseRequestLineMakePurchaseOrder(models.TransientModel):
    _inherit = 'purchase.request.line.make.purchase.order'

    def make_purchase_order(self):
        purchase_obj = self.env["purchase.order"]
        purchase = False

        for item in self.item_ids:
            if self.purchase_order_id:
                purchase = self.purchase_order_id
            if not purchase:
                po_data = self._prepare_purchase_order(
                    line.request_id.picking_type_id,
                    line.request_id.group_id,
                    line.company_id,
                    line.origin,
                    self.is_egp
                )
                purchase = purchase_obj.create(po_data)

        res = super().make_purchase_order()
        purchase_requests = self.item_ids.mapped("request_id")
        purchase_requests.action_del_egp_status()
        return res

    @api.model
    def _prepare_purchase_order(self, picking_type, group_id, company, origin, egp=False):
        data = super()._prepare_purchase_order(picking_type, group_id, company, origin)
        if egp:
            data["state"] = "purchase"

        return data
