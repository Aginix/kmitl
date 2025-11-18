# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    stock_valuation_layer_ids = fields.One2many(
        comodel_name='stock.valuation.layer',
        inverse_name='stock_move_id',
        string='Stock Valuation Layers',
        compute='_compute_valuation_layers',
        store=False,
    )

    def _compute_valuation_layers(self):
        for picking in self:
            picking.stock_valuation_layer_ids = self.env['stock.valuation.layer'].search([
                ('stock_move_id', 'in', picking.move_ids.ids)
            ])
