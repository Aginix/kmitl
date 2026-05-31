# -*- coding: utf-8 -*-
from odoo import fields, models

from .assignment import AssignedOfficerMixin


class PurchaseOrder(AssignedOfficerMixin, models.Model):
    _inherit = "purchase.order"

    _assign_user_group = "purchase.group_purchase_user"
    _assign_manager_group = "purchase.group_purchase_manager"

    assigned_to = fields.Many2one(
        comodel_name="res.users",
        string="เจ้าหน้าที่ผู้รับผิดชอบ",
        copy=False,
        index=True,
        tracking=True,
    )
    assignment_can_assign_me = fields.Boolean(
        compute="_compute_assignment_can_assign_me",
    )
