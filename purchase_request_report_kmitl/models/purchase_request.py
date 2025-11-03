# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class PurchaseRequest(models.Model):
    _name = 'purchase.request'
    _inherit = ['purchase.request', 'thai.date.mixin']
