# -*- coding: utf-8 -*-
from lxml import etree

from odoo import _, api, fields, models


class PurchaseRequestApproval(models.Model):
    _name = "purchase.request.approval"
    _inherit = ["purchase.request.approval", "tier.validation"]
    _state_from = ["submitted"]
    _state_to = ["approved"]

    _tier_validation_manual_config = False

    is_approval = fields.Boolean(compute="_compute_is_purchase_request_approval")

    def _compute_is_purchase_request_approval(self):
        for rec in self:
            rec.is_approval = rec._name == "purchase.request.approval"

    @api.model
    def _get_under_validation_exceptions(self):
        res = super(PurchaseRequestApproval, self)._get_under_validation_exceptions()
        res.append("route_id")
        return res

    def button_draft(self):
        self.mapped("review_ids").unlink()
        return super().button_draft()

    def _add_tier_validation_buttons(self, node, params):
        if self.is_approval:
            str_element = self.env["ir.qweb"]._render(
                "base_tier_validation.tier_validation_buttons", params
            )
            new_node = etree.fromstring(str_element)
            return new_node
        return etree.Element("div")
