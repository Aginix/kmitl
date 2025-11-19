# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class PurchaseContractType(models.Model):
    _name = 'purchase.contract.type'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'PurchaseContractType'

    name = fields.Char(tracking=True, required=True)
    active = fields.Boolean(tracking=True, default=True)
    purchase_ids = fields.One2many(
        comodel_name="purchase.order",
        inverse_name="contract_type_id",
    )
    is_construction = fields.Boolean(tracking=True, default=False)
