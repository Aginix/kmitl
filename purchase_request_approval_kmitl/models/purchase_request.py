# -*- coding: utf-8 -*-
from lxml import etree

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"
    _state_from = ["to_verify", "to_approve"]

    _STATES = [("to_verify", "To be verified"), ("to_approve",)]

    is_purchase_request = fields.Boolean(compute="_compute_is_purchase_request")
    state = fields.Selection(
        selection_add=_STATES,
        string="Status",
        index=True,
        tracking=True,
        required=True,
        copy=False,
        ondelete={
            "to_verify": "set default",
        },
    )

    can_request = fields.Boolean(compute="_compute_can_request")

    def _compute_is_purchase_request(self):
        for rec in self:
            rec.is_purchase_request = rec._name == "purchase.request"

    def _add_tier_validation_buttons(self, node, params):
        """ "close btn"""
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
            return self.button_approved()

    def _compute_to_approve_allowed(self):
        super()._compute_to_approve_allowed()
        for rec in self:
            rec.to_approve_allowed = rec.state == "to_verify" and any(
                not line.cancelled and line.product_qty for line in rec.line_ids
            )

    @api.model
    def _get_after_validation_exceptions(self):
        res = super()._get_after_validation_exceptions()
        res.append("state")
        res.append("substate_id")
        return res

    def button_to_verify(self):
        self.ensure_one()
        if self.detect_exceptions() and not self.ignore_exception:
            return self._popup_exceptions()
        self.write({"state": "to_verify"})

    @api.depends("state")
    def _compute_is_editable(self):
        res = super()._compute_is_editable()
        for record in self:
            if record.state in ("to_verify"):
                record.is_editable = False

    def request_validation(self):
        self.ensure_one()
        res = super().request_validation()
        self.button_to_approve()
        return res

    def restart_validation(self):
        self.ensure_one()
        res = super().restart_validation()
        self.write({"state": "to_verify"})
        return res

    @api.model
    def _get_under_validation_exceptions(self):
        res = super()._get_under_validation_exceptions()
        res.append("state")
        res.append("substate_id")
        res.append("approved_by")
        res.append("date_verified")
        res.append("date_approved")
        return res

    @api.depends("requested_by")
    def _compute_can_request(self):
        current_user = self.env.user
        is_manager = current_user.has_group(
            "purchase_request.group_purchase_request_manager"
        )
        is_admin = current_user.has_group("base.group_erp_manager")
        for rec in self:
            own_by_me = rec.requested_by.id == current_user.id
            rec.can_request = own_by_me or is_manager or is_admin

    def _compute_hide_reserve_budget_button(self):
        super()._compute_hide_reserve_budget_button()
        for rec in self:
            if rec.state == "to_verify":
                rec.hide_reserve_budget_button = False

    def _compute_is_budget_editable(self):
        super()._compute_is_budget_editable()
        can_edit = self.env.user.has_group("budget.group_budget_commitment")
        for rec in self:
            if rec.substate_sequence == 10 and rec.state == "to_verify" and can_edit:
                rec.is_budget_editable = True
