# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class StockScrap(models.Model):
    _inherit = 'stock.scrap'

    attachment_ids = fields.One2many(
        'ir.attachment',
        'res_id',               
        string='Document Attachments',
        tracking=True,
        states={'done': [('readonly', True)]}
    )