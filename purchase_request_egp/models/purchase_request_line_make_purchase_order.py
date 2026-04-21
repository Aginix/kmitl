# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class PurchaseRequestLineMakePurchaseOrder(models.TransientModel):
    _inherit = 'purchase.request.line.make.purchase.order'

    def make_purchase_order(self):
        res = super().make_purchase_order()
        purchase_requests = self.item_ids.mapped("request_id")
        if purchase_requests.is_egp:
            purchase_requests.action_del_egp_status()
            purchase_requests.button_done()
            res_id = res['domain'][0][2].pop()
            return {
                "name": _("Purchase Order"),
                "type": "ir.actions.act_window",
                "res_model": "purchase.order",
                "view_mode": "form",
                "res_id": res_id,
                "view_id": False,
                "context": False,
            }
        return res

    @api.model
    def _prepare_purchase_order(self, picking_type, group_id, company, origin):
        data = super()._prepare_purchase_order(picking_type, group_id, company, origin)
        purchase_request = self.item_ids.mapped('request_id')
        if purchase_request.is_egp:
            data["state"] = "draft"
        return data
