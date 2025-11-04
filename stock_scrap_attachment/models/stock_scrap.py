# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class StockScrap(models.Model):
    _inherit = 'stock.scrap'

    attachment_ids = fields.Many2many(
        'ir.attachment',
        'stock_scrap_ir_attachment_rel',
        'scrap_id',                        
        'attachment_id',                   
        string='Document Attachments',
        tracking=True,
        states={'done': [('readonly', True)]}
    )