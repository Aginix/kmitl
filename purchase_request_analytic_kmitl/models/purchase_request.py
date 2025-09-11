# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class PurchaseRequest(models.Model):
    _name = 'purchase.request'
    _inherit = ['purchase.request', 'analytic.distribution.mixin']
