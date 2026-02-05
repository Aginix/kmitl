# -*- coding: utf-8 -*-
import logging

from odoo import models, fields

_logger = logging.getLogger(__name__)


class PurchaseRequestLine(models.Model):
    _inherit = 'purchase.request.line'

    # Override name field to be Text instead of Char
    # Merged from: purchase_request_line_name_text
    name = fields.Text(string="Description", tracking=True)
