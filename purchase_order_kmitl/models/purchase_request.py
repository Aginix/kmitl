# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class PurchaseRequest(models.Model):
    _inherit = 'purchase.request'

    order_ids = fields.One2many(
        "purchase.order",
        "request_id",
        string="Purchase Orders"
    )
