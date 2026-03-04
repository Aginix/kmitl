# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class StockScrap(models.Model):
    _inherit = 'stock.scrap'

    reason = fields.Text(
        string="Reason",
        states={'done': [('readonly', True)]},
        tracking=True
    )