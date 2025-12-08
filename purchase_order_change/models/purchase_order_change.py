# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class PurchaseOrderChange(models.Model):
    _name = 'purchase.order.change'
    _description = 'Purchase Order Change'

    number = fields.Integer(string='Number')
    date = fields.Date(string='Date', default=fields.Date.context_today)
    change_type = fields.Selection(selection=[('none', 'None'), ('impact', 'Impact')])
    section_ids = fields.Many2many(comodel_name="purchase.change.section")
    state = fields.Selection(selection=[("draft", "Draft"), ("done", "Done")] , default="draft")
    purchase_id = fields.Many2one(comodel_name="purchase.order")

