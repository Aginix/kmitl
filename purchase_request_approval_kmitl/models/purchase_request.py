# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class PurchaseRequest(models.Model):
    _inherit = 'purchase.request'

    _STATES = [
        ("to_verify", "To be verified"),
        ("to_approve",)
    ]

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
        }
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
            if record.state in ("to_verify"):
                record.is_editable = False

    @api.depends("requested_by")
    def _compute_can_request(self):
        current_user = self.env.user
        is_manager = current_user.has_group("purchase_request.group_purchase_request_manager")
        for rec in self:
            rec.can_request = (rec.requested_by.id == current_user.id) or is_manager
