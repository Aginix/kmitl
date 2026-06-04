# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class StockInventory(models.Model):
    _inherit = 'stock.inventory'

    department_analytic_id = fields.Many2one(
        comodel_name="account.analytic.account",
        string="Department",
        domain=[("root_plan_id.code", "=", "departments")],
    )
