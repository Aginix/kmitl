# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class PurchaseRequestTender(models.Model):
    _name = 'purchase.request.tender'
    _description = 'Purchase Request Tender'

    name = fields.Char(string='Tender Name', required=True, tracking=True)
    price = fields.Monetary(string="Price", required=True, tracking=True)
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        required=True,
        default=lambda self: self.env.company.currency_id.id,
    )
    sequence = fields.Integer(default=10)
    request_id = fields.Many2one("purchase.request", required=True, index=True)
