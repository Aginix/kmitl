# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class PurchaseRequestTender(models.Model):
    _name = 'purchase.request.tender'
    _description = 'Purchase Request Tender'

    name = fields.Char(string='Tender Name', required=True, tracking=True)
    price = fields.Monetary(string="Price", required=True, tracking=True)
    company_id = fields.Many2one(related="request_id.company_id", readonly=True)
    currency_id = fields.Many2one(related="request_id.company_id.currency_id", readonly=True)
    sequence = fields.Integer(default=10)
    request_id = fields.Many2one("purchase.request", required=True, index=True)
