# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    change_ids = fields.One2many(
        comodel_name='purchase.order.change',
        inverse_name='purchase_id',
        string='Purchase Order Changes'
    )
