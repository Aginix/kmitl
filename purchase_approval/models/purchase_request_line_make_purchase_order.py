# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class PurchaseRequestLineMakePurchaseOrder(models.TransientModel):
    _inherit = 'purchase.request.line.make.purchase.order'

    def _prepare_purchase_order(self, picking_type, group_id, company, origin):
        res = super()._prepare_purchase_order(picking_type, group_id, company, origin)
        active_id = self.env.context.get("active_id", False)
        purchase_request = self.env['purchase.request'].browse(active_id)
        if purchase_request.is_required_approval:
            res['request_id'] = purchase_request.id
        return res

    def make_purchase_order(self):
        res = super().make_purchase_order()
        purchase_id = res['domain'][0][2]
        purchase = self.env['purchase.order'].browse(purchase_id)
        if purchase.request_id:
            return {
                "name": _("Purchase Approval"),
                "res_id": purchase.id,
                "view_mode": "form",
                "res_model": "purchase.order",
                "view_id": self.env.ref("purchase_approval.view_purchase_approval_form").id,
                "context": False,
                "type": "ir.actions.act_window",
            }
        return res
