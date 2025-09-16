# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class PurchaseRequestLineMakePurchaseOrder(models.TransientModel):
    _inherit = 'purchase.request.line.make.purchase.order'

    def make_purchase_order(self):
        res = super().make_purchase_order()
        purchase_requests = self.item_ids.mapped("request_id")
        purchase_requests.action_del_egp_status()
        return res
