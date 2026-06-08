# -*- coding: utf-8 -*-
from odoo import fields, models


class StockScrap(models.Model):
    _inherit = "stock.scrap"

    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Created By",
        readonly=True,
        default=lambda self: self.env.user,
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

    attachment_ids = fields.Many2many(
        comodel_name="ir.attachment",
        string="Document Attachments",
        domain=[("res_model", "=", "stock.scrap")],
        context={"default_res_model": "stock.scrap"},
        tracking=True,
        states={"done": [("readonly", True)]},
    )
