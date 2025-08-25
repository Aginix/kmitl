# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseOrderBidderLine(models.Model):
    _name = 'purchase.order.bidder.line'
    _description = 'PurchaseOrderBidderLine'

    name = fields.Char('Name')

    order_id = fields.Many2one('purchase.order', string='Purchase Order', ondelete='cascade')
    bidder_id = fields.Many2one(
    'res.partner',
    string='Bidder',
    required=True,
    domain="[('supplier_rank', '>', 0)]"
)
    price_offer = fields.Float(string='Offer price', required=True)