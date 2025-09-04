# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


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
            if rec.is_egp:
                rec.egp_status = "in_progress"

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
                if rec.is_egp and rec.state == "approved":
                    rec.egp_status = "waiting"
                if rec.is_egp and rec.state == "done":
                    rec.egp_status = "done"
        return res

    def action_create_rfq(self):
        for rec in self:
            if not rec.egp_project_id and rec.is_egp:
                raise UserError("ไม่สามารถสร้าง PO ได้ เพราะไม่ใช่ e-GP เลขที่โครงการ")

        action = self.env.ref("purchase_request.action_purchase_request_line_make_purchase_order").read()[0]
        return action
