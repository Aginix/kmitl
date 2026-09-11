# -*- coding: utf-8 -*-
from odoo import api, fields, models

from .assignment import AssignedOfficerMixin


class PurchaseRequestApproval(AssignedOfficerMixin, models.Model):
    _inherit = "purchase.request.approval"

    # PA carries its own Assigned Officer, independent of the parent PR.
    # See docs/adr/0006-pa-independent-assigned-officer.md.
    # Note: PA's `assigned_to` is the Approver (manager who signs off); the
    # officer lives on `pa_assigned_to`.
    _assign_field = "pa_assigned_to"
    _assign_user_group = "purchase_request.group_purchase_request_user"
    _assign_manager_group = "purchase_request.group_purchase_request_manager"

    # PR's officer, shown alongside PA's own officer for coordination context.
    pr_assigned_to = fields.Many2one(
        comodel_name="res.users",
        related="request_id.assigned_to",
        string="PR Assigned Officer",
    )

    pa_assigned_to = fields.Many2one(
        comodel_name="res.users",
        string="Assigned Officer",
        tracking=True,
        copy=False,
        index=True,
    )
    assignment_can_assign_me = fields.Boolean(
        compute="_compute_assignment_can_assign_me",
    )

    @api.depends("pa_assigned_to")
    def _compute_assignment_can_assign_me(self):
        return super()._compute_assignment_can_assign_me()
