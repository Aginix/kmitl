# -*- coding: utf-8 -*-
from odoo import models


class PurchaseRequest(models.Model):
    _name = "purchase.request"
    _inherit = ['purchase.request', 'state.leadtime.mixin']

    _excluded_transitions = [('*', 'rejected')]
