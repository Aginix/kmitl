# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class PurchaseRequest(models.Model):
    _inherit = 'purchase.request'

    _STATES = [
        ("waiting", "Waiting for e-GP"),
        ("in_progress", "In progress e-GP"),
        ("done", "done e-GP")
    ]

    egp_status = fields.Selection(
        selection=_STATES,
        string="e-GP Status",
        tracking=True,
    )
    can_edit_egp = fields.Boolean(
        compute="_compute_can_edit_egp",
        default=False,
    )

    def action_set_egp_waiting(self):
        for rec in self:
            rec.egp_status = "waiting"

    @api.depends_context("uid")
    def _compute_can_edit_egp(self):
        for rec in self:
            rec.can_edit_egp = self.env.user.has_group(
                "purchase_request_security.group_purchase_request_user_all"
            )

    @api.depends("estimated_cost", "state")
    def _compute_is_egp(self):
        for record in self:
            record.is_egp = record.estimated_cost > 100000

    def write(self, vals):
        res = super().write(vals)
        for rec in self:
            if 'state' in vals:
                if rec.state == "in_progress":
                    rec.egp_status = "in_progress"
                if rec.state == "done":
                    rec.egp_status = "done"
        return res
