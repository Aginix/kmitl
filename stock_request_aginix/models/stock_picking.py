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

    def action_view_stock_request(self):
        self.ensure_one()
        if not self.stock_request_id:
            raise UserError(_("No Stock Request linked."))

        return {
            'type': 'ir.actions.act_window',
            'name': _('Stock Request'),
            'res_model': 'stock.request',
            'view_mode': 'form',
            'res_id': self.stock_request_id.id,
            'target': 'current',
        }
