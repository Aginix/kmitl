# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    code = fields.Selection(
        selection_add=[("stock_request_order", "Stock Request Order")],
        ondelete={"stock_request_order": "cascade"},
    )
