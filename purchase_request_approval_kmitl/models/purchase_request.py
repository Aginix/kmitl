# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    _STATES = [("to_verify", "To be verified"), ("to_submit",)]

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

    def button_to_verify(self):
        self.ensure_one()
        if self.detect_exceptions() and not self.ignore_exception:
            return self._popup_exceptions()
        self.write({"state": "to_verify"})

    @api.depends("state")
    def _compute_is_editable(self):
        res = super()._compute_is_editable()
        for record in self:
            if record.state != "draft":
                record.is_editable = False

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
            if rec.state == "to_verify" and can_edit:
                rec.is_budget_editable = True
