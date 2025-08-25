# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class AgreementLine(models.Model):
    _inherit = 'agreement.line'

    price_unit = fields.Float(string="Unit Price")

    price_subtotal = fields.Monetary(string="Total")

    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)

    product_categ_id = fields.Many2one(
        "product.category", 
        string="Product Category", 
    )