# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseCreateInvoicePlan(models.TransientModel):
    _inherit = 'purchase.create.invoice.plan'

    def purchase_create_invoice_plan(self):
        res = super().purchase_create_invoice_plan()
        purchase_id = self.env.context.get("default_purchase_id")
        if purchase_id:
            purchase = self.env["purchase.order"].browse(purchase_id)
            purchase.use_invoice_plan = True
        return res
