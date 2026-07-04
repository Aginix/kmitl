# -*- coding: utf-8 -*-
from odoo import fields, models


class PurchaseRequest(models.Model):
    _name = "purchase.request"
    _inherit = ["purchase.request", "assignment.mixin"]

    _assign_user_group = "purchase_request.group_purchase_request_user"
    _assign_manager_group = "purchase_request.group_purchase_request_manager"

    # Reuse the existing (OCA) field, repurposed as the Assigned Officer.
    assigned_to = fields.Many2one(
        string="Assigned Officer",
        tracking=True,
    )
