# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    is_purchase_request = fields.Boolean(compute="_compute_is_purchase_request")
    can_request = fields.Boolean(compute="_compute_can_request")

    def _compute_is_purchase_request(self):
        for rec in self:
            rec.is_purchase_request = rec._name == "purchase.request"

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

    def _check_pr_exceptions(self):
        """Pre-check exceptions. Pops a confirmation dialog if there are unresolved exceptions."""
        self.ensure_one()
        if self.detect_exceptions() and not self.ignore_exception:
            return self._popup_exceptions()
        return False
