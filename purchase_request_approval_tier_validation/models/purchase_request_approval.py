# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class PurchaseRequestApproval(models.Model):
    _name = 'purchase.request.approval'
    _inherit = ["purchase.request.approval", "tier.validation"]
    _state_from = ["to_approve"]
    _state_to = ["approved"]

    _tier_validation_manual_config = False

    @api.model
    def _get_under_validation_exceptions(self):
        res = super()._get_under_validation_exceptions()
        res.append("state")
        return res

    def _validate_tier(self, tiers=False):
        super()._validate_tier(tiers)
        reviews = self.review_ids.filtered(
            lambda r: r.status == "pending" and (self.env.user in r.reviewer_ids)
        )
        if not reviews:
            return self.button_approved()

    def _rejected_tier(self, tiers=False):
        super()._rejected_tier(tiers)
        reviews = self.review_ids.filtered(
            lambda r: r.status == "pending" and (self.env.user in r.reviewer_ids)
        )
        if not reviews:
            return self.button_rejected()

    @api.model
    def _get_after_validation_exceptions(self):
        res = super()._get_after_validation_exceptions()
        res.append("state")
        return res
