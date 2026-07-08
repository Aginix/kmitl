# -*- coding: utf-8 -*-
from odoo import fields, models


class PurchaseRequestApproval(models.Model):
    _inherit = "purchase.request.approval"

    pr_assigned_to = fields.Many2one(
        comodel_name="res.users",
        related="request_id.assigned_to",
        string="Assigned Officer",
    )
