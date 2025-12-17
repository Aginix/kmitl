# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    approval_count = fields.Integer(
        compute="_compute_purchase_request_approval_count",
        string="Purchase Request Approval Count"
    )

    def _compute_purchase_request_approval_count(self):
        Approval = self.env["purchase.request.approval"]
        for order in self:
            order.approval_count = Approval.search_count([
                ("request_id", "=", order.request_id.id)
            ])

    def action_view_purchase_request_approval(self):
        self.ensure_one()

        return {
            "type": "ir.actions.act_window",
            "name": "Purchase Request Approvals",
            "res_model": "purchase.request.approval",
            "view_mode": "form",
            "domain": [("request_id", "=", self.request_id.id)],
            "context": {
                "default_request_id": self.request_id.id,
            },
        }
