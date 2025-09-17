# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class PurchaseRequest(models.Model):
    _inherit = 'purchase.request'

    line_ids = fields.One2many(
        comodel_name="purchase.request.line",
        inverse_name="request_id",
        string="Products to Purchase",
        readonly=True,
        copy=True,
        tracking=True,
    )
