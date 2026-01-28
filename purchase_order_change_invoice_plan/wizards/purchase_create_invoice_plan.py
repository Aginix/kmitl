# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseCreateInvoicePlan(models.TransientModel):
    _inherit = 'purchase.create.invoice.plan'

    def purchase_create_invoice_plan(self):
        res = super().purchase_create_invoice_plan()
        purchase = self.env["purchase.order"].browse(self._context.get("active_id"))
        purchase.use_invoice_plan = True
        purchase.remove_invoice_plan()
        return res
