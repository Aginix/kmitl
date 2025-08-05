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
    bidder_id = fields.Many2one('res.users', string='ผู้เสนอราคา', required=True)
    price_offer = fields.Float(string='ราคาที่เสนอ', required=True)