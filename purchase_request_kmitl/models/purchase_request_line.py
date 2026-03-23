# -*- coding: utf-8 -*-
from odoo import fields, models


class PurchaseRequestLine(models.Model):
    _inherit = "purchase.request.line"

    name = fields.Text(string="Description", tracking=True)
