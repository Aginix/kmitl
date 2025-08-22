# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class PurchaseRequestApprovalForm(models.Model):
    _inherit = ["purchase.request.approval.form", "base.exception"]
    _name = "purchase.request.approval.form"
    _order = "main_exception_id asc, id desc"

    @api.model
    def test_all_draft_requests(self):
        approval_set = self.search([("state", "=", "draft")])
        approval_set.detect_exceptions()
        return True

    @api.model
    def _reverse_field(self):
        return "pr_approval_form_ids"

    def detect_exceptions(self):
        all_exceptions = super().detect_exceptions()
        lines = self.mapped("line_ids")
        all_exceptions += lines.detect_exceptions()
        return all_exceptions

    @api.constrains("ignore_exception", "line_ids", "state")
    def purchase_request_check_exception(self):
        requests = self.filtered(lambda s: s.state == "submitted")
        if requests:
            requests._check_exception()

    @api.onchange("line_ids")
    def onchange_ignore_exception(self):
        if self.state == "submitted":
            self.ignore_exception = False

    def action_merge_to_submitted(self):
        if self.detect_exceptions() and not self.ignore_exception:
            return self._popup_exceptions()
        return super().action_merge_to_submitted()

    def button_draft(self):
        res = super().button_draft()
        for request in self:
            request.exception_ids = False
            request.main_exception_id = False
            request.ignore_exception = False
        return res

    @api.model
    def _get_popup_action(self):
        action = self.env.ref(
            "purchase_request_approval_exception_kmitl.action_purchase_request_approval_exception_confirm"
        )
        return action

