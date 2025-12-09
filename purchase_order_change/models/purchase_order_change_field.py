# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class PurchaseOrderChangeField(models.Model):
    _name = 'purchase.order.change.field'
    _description = 'Purchase Order Change Field'

    change_id = fields.Many2one(comodel_name="purchase.order.change")
    section_id = fields.Many2one(comodel_name="purchase.change.section") #ไม่รู้จำเป็นต้องใช้ไหม
    field_id = fields.Many2one(comodel_name="ir.model.fields")
    old_value = fields.Char(string='Old Value')
    new_value = fields.Char(string='New Value')
    field_name = fields.Char(string='Field Name')
