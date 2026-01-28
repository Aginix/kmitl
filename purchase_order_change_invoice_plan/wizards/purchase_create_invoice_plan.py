# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseCreateInvoicePlan(models.TransientModel):
    _inherit = 'purchase.create.invoice.plan'

    def purchase_create_invoice_plan(self):
        self.ensure_one()

        purchase_id = self._context.get("default_purchase_id")

        if not purchase_id:
            purchase_id = self._context.get("active_id")

        purchase = self.env["purchase.order"].browse(purchase_id)
        purchase.create_invoice_plan(
            self.num_installment,
            self.installment_date,
            self.interval,
            self.interval_type,
        )
        purchase.use_invoice_plan = True
        return {"type": "ir.actions.act_window_close"}
