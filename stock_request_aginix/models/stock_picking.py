# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    stock_request_id = fields.One2many(
        'stock.request',
        'picking_id',
        string='Stock Requests'
    )
    
    has_stock_request = fields.Boolean(
        string='Has Stock Request',
        compute='_compute_has_stock_request',
        store=True
    )
    
    @api.depends('stock_request_id')
    def _compute_has_stock_request(self):
        for record in self:
            record.has_stock_request = bool(record.stock_request_id)

    def action_view_stock_request(self):
        self.ensure_one()
        if not self.stock_request_id:
            raise UserError(_("No Stock Request linked."))

        return {
            'type': 'ir.actions.act_window',
            'name': _('Stock Request'),
            'res_model': 'stock.request',
            'view_mode': 'form',
            'res_id': self.stock_request_id[0].id,
            'target': 'current',
        }
