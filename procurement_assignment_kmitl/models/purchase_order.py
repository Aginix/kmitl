# -*- coding: utf-8 -*-
from odoo import fields, models


class PurchaseOrder(models.Model):
    _name = "purchase.order"
    _inherit = ["purchase.order", "assignment.mixin"]

    _assign_user_group = "purchase.group_purchase_user"
    _assign_manager_group = "purchase.group_purchase_manager"

    assigned_to = fields.Many2one(
        comodel_name="res.users",
        string="Assigned Officer",
        copy=False,
        index=True,
        tracking=True,
    )
