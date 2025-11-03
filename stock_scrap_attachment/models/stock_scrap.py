# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class StockScrap(models.Model):
    _inherit = 'stock.scrap'

    attachment_ids = fields.Many2many(
        'ir.attachment',
        'stock_scrap_ir_attachment_rel',  # ชื่อตารางกลาง
        'scrap_id',                        # column สำหรับ stock.scrap id
        'attachment_id',                   # column สำหรับ ir.attachment id
        string='Document Attachments',
        tracking=True,
        states={'done': [('readonly', True)]}
    )