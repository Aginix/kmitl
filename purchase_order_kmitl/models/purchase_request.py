# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class PurchaseRequest(models.Model):
    _inherit = 'purchase.request'

    order_id = fields.Many2one(
        "purchase.order",
        string="PO",
        related='approval_id.order_id'
    )
