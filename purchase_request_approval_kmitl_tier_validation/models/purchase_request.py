# -*- coding: utf-8 -*-
from lxml import etree

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class PurchaseRequest(models.Model):
    _inherit = 'purchase.request'
    _state_from = ["to_verify", "to_approve"]

    def _add_tier_validation_buttons(self, node, params):
        """"close btn"""
        if self.is_purchase_request:
            str_element = self.env["ir.qweb"]._render(
                "base_tier_validation.tier_validation_buttons", params
            )
            new_node = etree.fromstring(str_element)
            return new_node
        return etree.Element("div")

    def _validate_tier(self, tiers=False):
        super()._validate_tier(tiers)
        reviews = self.review_ids.filtered(
            lambda r: r.status == "pending" and (self.env.user in r.reviewer_ids)
        )
        if not reviews:
            return self.write({'state': 'approved'})

    @api.model
    def _get_after_validation_exceptions(self):
        res = super()._get_after_validation_exceptions()
        res.append("state")
        res.append("substate_id")
        return res

    @api.model
    def _get_under_validation_exceptions(self):
        res = super()._get_under_validation_exceptions()
        res.append("state")
        res.append("substate_id")
        return res

    def request_validation(self):
        self.ensure_one()
        res = super().request_validation()
        self.write({"state": "to_approve"})
        return res

    def restart_validation(self):
        self.ensure_one()
        res = super().restart_validation()
        self.write({"state": "to_verify"})
        return res
