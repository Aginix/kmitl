# -*- coding: utf-8 -*-
from datetime import datetime

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class StockInventory(models.Model):
    _inherit = 'stock.inventory'

    READONLY_STATES = {
        "draft": [("readonly", False)],
    }

    def _default_inventory_name(self):
        today_str = datetime.today().strftime('%d-%m-%Y')
        return f'Inventory Adjustment {today_str}'

    def _default_owner(self):
        return self.env.user.partner_id.id

    name = fields.Char(
        default=_default_inventory_name,
    )
    product_selection = fields.Selection(
        [
            ("all", "All Products"),
            ("manual", "Manual Selection"),
            ("category", "Product Category"),
            ("one", "One Product"),
        ],
        default="all",
        required=True,
        readonly=True,
        states=READONLY_STATES,
    )
    owner_id = fields.Many2one(
        "res.partner",
        default=_default_owner,
    )
