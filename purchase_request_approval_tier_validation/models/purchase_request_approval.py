# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class PurchaseRequestApproval(models.Model):
    _name = "purchase.request.approval"
    _inherit = ["purchase.request.approval", "tier.validation"]
    _state_from = ["submitted"]
    _state_to = ["approved"]

    _tier_validation_manual_config = False

    @api.model
    def _get_under_validation_exceptions(self):
        res = super(PurchaseRequestApproval, self)._get_under_validation_exceptions()
        res.append("route_id")
        return res

    def button_draft(self):
        self.mapped("review_ids").unlink()
        return super().button_draft()
