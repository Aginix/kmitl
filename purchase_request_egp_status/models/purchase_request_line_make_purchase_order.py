# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class PurchaseRequestLineMakePurchaseOrder(models.TransientModel):
    _inherit = 'purchase.request.line.make.purchase.order'

    def make_purchase_order(self):
        purchase_requests = self.item_ids.mapped("request_id")
        purchase_requests.action_egp_in_progress()
        return super().make_purchase_order()
