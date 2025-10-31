# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    group_enable_create_bill = fields.Boolean(
        string="Allow Create Bill from Purchase Order",
        implied_group="purchase_order_hide_create_bill_button.group_enable_create_bill",
        help="Enable the 'Create Bill' button in Purchase Orders.",
    )
