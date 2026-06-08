# -*- coding: utf-8 -*-
from odoo import fields, models


class StockScrap(models.Model):
    _inherit = "stock.scrap"

    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Created By",
        readonly=True,
        default=lambda self: self.env.user,
        states={"done": [("readonly", True)]},
        tracking=True,
    )

    reason = fields.Text(
        string="Reason",
        states={"done": [("readonly", True)]},
        tracking=True,
    )

    origin = fields.Char(
        states={"done": [("readonly", True)]},
    )
