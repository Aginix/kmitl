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

    @api.depends('line_ids.purchase_lines')
    def _compute_egp_status(self):
        for rec in self:
            if rec.line_ids.mapped('purchase_lines'):
                rec.egp_status = False

    def button_draft(self):
        res = super().button_draft()
        self.write({"egp_status": False})
        return res

    def action_egp_in_progress(self):
        for record in self:
            if record.is_egp:
                record.egp_status = "in_progress"

    @api.depends_context("uid")
    def _compute_can_edit_egp(self):
        user_in_group = self.env.user.has_group(
            "purchase_request_security.group_purchase_request_user_all"
        )
        for record in self:
            record.can_edit_egp = bool(user_in_group and record.egp_status == "waiting")

    @api.depends("estimated_cost", "state")
    def _compute_is_egp(self):
        for record in self:
            record.is_egp = record.estimated_cost > 100000

    def write(self, vals):
        res = super().write(vals)
        for record in self:
            if 'state' in vals and record.is_egp:
                if record.state == "approved":
                    record.egp_status = "waiting"
                elif record.state == "done":
                    record.egp_status = "done"
        return res

    def action_create_rfq(self):
        for record in self:
            if record.is_egp and record.egp_status not in ['in_progress']:
                raise UserError("ท่านสามารถสร้างใบสั่งซื้อ/จ้างได้เมื่ออยู่ในกระบวนการ e-GP เท่านั้น")

        action = self.env.ref("purchase_request.action_purchase_request_line_make_purchase_order").sudo().read()[0]
        return action
