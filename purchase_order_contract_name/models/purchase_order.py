# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    contract_name = fields.Char(
        string="ชื่อสัญญา/ใบสั่งซื้อ/จ้าง",
        tracking=True,
        states=READONLY_STATES,
    )
