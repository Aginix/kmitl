# -*- coding: utf-8 -*-
from datetime import datetime

from odoo import fields, models


class StockInventory(models.Model):
    _inherit = "stock.inventory"

    def _default_inventory_name(self):
        today_str = datetime.today().strftime("%d-%m-%Y")
        return f"Inventory Adjustment {today_str}"

    name = fields.Char(
        default=_default_inventory_name,
    )

    responsible_id = fields.Many2one(
        comodel_name="res.users",
        default=lambda self: self.env.user,
    )

    department_id = fields.Many2one(
        comodel_name="hr.department",
        string="Department",
    )
