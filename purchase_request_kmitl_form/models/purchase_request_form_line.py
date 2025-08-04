# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseRequestFormLine(models.Model):
    _name = 'purchase.request.form.line'
    _description = 'PurchaseRequestFormLine'

    pr2_id = fields.Many2one('purchase.request.form', string='PR2')
    product_id = fields.Many2one('product.product', string='Product', required=True)
    quantity = fields.Float(string='Quantity')
    description = fields.Text(string='Description')

    unit_price = fields.Float(string='Unit Price')
    taxes = fields.Many2many('account.tax', string='Taxes')

    subtotal = fields.Monetary(string='Subtotal', compute='_compute_subtotal', store=True)
    currency_id = fields.Many2one(related='pr2_id.currency_id', store=True, readonly=True)

    @api.depends('quantity', 'unit_price')
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.quantity * line.unit_price
