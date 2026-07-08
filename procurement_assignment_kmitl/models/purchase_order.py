# -*- coding: utf-8 -*-
from odoo import _, fields, models


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

    def _assignment_activity_summary(self):
        return _("Assigned as responsible procurement officer")

    def _assignment_takeover_param(self):
        return "procurement_assignment_kmitl.allow_takeover_assigned"
