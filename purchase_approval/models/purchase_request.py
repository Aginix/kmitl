# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    is_required_approval = fields.Boolean(
        compute="_compute_is_required_approval", store=False, readonly=True
    )

    purchase_approval_count = fields.Integer(
        string="PR2s count", compute="_compute_purchase_approval_count", readonly=True
    )

    @api.depends("estimated_cost")
    def _compute_is_required_approval(self):
        for rec in self:
            rec.is_required_approval = rec.estimated_cost <= 100000

    def action_view_purchase_approval(self):
        action = self.env["ir.actions.actions"]._for_xml_id("purchase_approval.action_purchase_approval")
        lines = self.mapped("line_ids.purchase_lines.order_id")
        if len(lines) > 1:
            action["domain"] = [("id", "in", lines.ids)]
        elif lines:
            action["views"] = [
                (self.env.ref("purchase_approval.view_purchase_approval_form").id, "form")
            ]
            action["res_id"] = lines.id
        return action

    @api.depends("line_ids")
    def _compute_purchase_approval_count(self):
        for rec in self:
            rec.purchase_approval_count = len(rec.mapped("line_ids.purchase_lines.order_id").filtered("request_id"))
