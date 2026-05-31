# -*- coding: utf-8 -*-
from odoo import fields, models

from .assignment import AssignedOfficerMixin


class PurchaseRequest(AssignedOfficerMixin, models.Model):
    _inherit = "purchase.request"

    _assign_user_group = "purchase_request.group_purchase_request_user"
    _assign_manager_group = "purchase_request.group_purchase_request_manager"

    # Reuse the existing (OCA) field, repurposed as the Assigned Officer.
    assigned_to = fields.Many2one(
        string="เจ้าหน้าที่ผู้รับผิดชอบ",
        tracking=True,
    )
    assignment_can_assign_me = fields.Boolean(
        compute="_compute_assignment_can_assign_me",
    )
