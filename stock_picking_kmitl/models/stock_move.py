# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class StockMove(models.Model):
    _inherit = 'stock.move'

    qty_available = fields.Float(
        string='On Hand Quantity',
        compute='_compute_qty_available',
        store=False
    )

    @api.depends('product_id', 'location_id')
    def _compute_qty_available(self):
        for move in self:
            if move.product_id and move.location_id:
                available = move.product_id.with_context(
                    location=move.location_id.id
                ).qty_available
                move.qty_available = abs(available)
            else:
                move.qty_available = 0.0