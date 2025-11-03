# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class StockScrap(models.Model):
    _inherit = 'stock.scrap'

    origin = fields.Char(
        states={'done': [('readonly', True)]}
    )