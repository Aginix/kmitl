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

    name = fields.Char(
        default=_default_inventory_name,
    )

    responsible_id = fields.Many2one(
        comodel_name="res.users",
        default=lambda self: self.env.user,
    )
