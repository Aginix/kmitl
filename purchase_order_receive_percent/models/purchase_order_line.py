# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    received_qty_percent = fields.Float(
        string='Received percent',
        compute='_compute_received_qty_percent',
        store=True,
        digits=(16, 2)
    )

    @api.depends('product_qty', 'qty_received')
    def _compute_received_qty_percent(self):
        for line in self:
            if line.product_qty:
                line.received_qty_percent = (line.qty_received / line.product_qty)
            else:
                line.received_qty_percent = 0.0
