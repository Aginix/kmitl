# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class StockValuationLayer(models.Model):
    _inherit = 'stock.valuation.layer'

    quantity_unsigned = fields.Float(
        string='Quantity',
        compute='_compute_abs_values',
        store=False
    )
    
    value_unsigned = fields.Float(
        string='Value',
        compute='_compute_abs_values',
        store=False
    )
    
    unit_cost_unsigned = fields.Float(
        string='Unit Cost',
        compute='_compute_abs_values',
        store=False
    )

    @api.depends('quantity', 'value', 'unit_cost')
    def _compute_abs_values(self):
        for layer in self:
            layer.quantity_unsigned = abs(layer.quantity)
            layer.value_unsigned = abs(layer.value)
            layer.unit_cost_unsigned = abs(layer.unit_cost) if layer.unit_cost else 0.0