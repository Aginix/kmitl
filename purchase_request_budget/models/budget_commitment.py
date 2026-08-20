# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class BudgetCommitment(models.Model):
    _inherit = "budget.commitment"

    purchase_request_ids = fields.One2many(
        "purchase.request",
        "budget_commitment_id",
        string="ใบขอให้จัดหา",
        help=(
            "ใบขอให้จัดหาที่ผูกกับใบจองนี้ ทั้งที่จองงบใหม่จาก พจ. เอง "
            "และที่หยิบใบจองนี้ไปใช้ (draw down)"
        ),
    )
    purchase_request_count = fields.Integer(
        compute="_compute_purchase_request_count",
    )

    @api.depends("purchase_request_ids")
    def _compute_purchase_request_count(self):
        # sudo the count so opening the commitment form never raises for a
        # budget viewer who lacks purchase.request read access; the button click
        # (action_view_purchase_requests) still runs in the user's own context.
        PurchaseRequest = self.env["purchase.request"].sudo()
        for rec in self:
            rec.purchase_request_count = PurchaseRequest.search_count(
                [("budget_commitment_id", "=", rec.id)]
            )

    def action_view_purchase_requests(self):
        self.ensure_one()
        action = {
            "type": "ir.actions.act_window",
            "name": _("ใบขอให้จัดหา"),
            "res_model": "purchase.request",
            "domain": [("budget_commitment_id", "=", self.id)],
            "context": {"create": False},
        }
        if self.purchase_request_count == 1:
            action.update(view_mode="form", res_id=self.purchase_request_ids.id)
        else:
            action["view_mode"] = "tree,form"
        return action
