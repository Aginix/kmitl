# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class PurchaseOrderBidderLine(models.Model):
    _name = 'purchase.order.bidder.line'
    _description = 'PurchaseOrderBidderLine'

    name = fields.Char(related='bidder_id.name', string='Bidder Name', readonly=True)
    order_id = fields.Many2one('purchase.order', string='Purchase Order', ondelete='cascade')
    bidder_id = fields.Many2one(
        'res.partner',
        string='Bidder',
        required=True,
        domain="[('supplier_rank', '>', 0)]"
    )
    price_offer = fields.Float(string='Offer price', required=True)
