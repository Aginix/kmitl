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