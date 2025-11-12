# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class AccountMoveRequest(models.Model):
    _inherit = ["account.move.request", "base.exception"]
    _name = "account.move.request"
    _order = "main_exception_id asc, id desc"

    @api.model
    def _reverse_field(self):
        return "move_request_ids"

    def detect_exceptions(self):
        all_exceptions = super().detect_exceptions()
        lines = self.mapped("line_ids")
        all_exceptions += lines.detect_exceptions()
        return all_exceptions

    @api.constrains("ignore_exception", "line_ids", "state")
    def account_move_request_check_exception(self):
        move_request = self.filtered(lambda s: s.state == "submitted")
        if move_request:
            move_request._check_exception()

    @api.onchange("line_ids")
    def onchange_ignore_exception(self):
        if self.state == "submitted":
            self.ignore_exception = False

    def action_submit(self):
        if self.detect_exceptions() and not self.ignore_exception:
            return self._popup_exceptions()
        return super().action_submit()

    def action_draft(self):
        for record in self:
            record.exception_ids = False
            record.main_exception_id = False
            record.ignore_exception = False
            record.state = "draft"
        return True

    @api.model
    def _get_popup_action(self):
        action = self.env.ref(
            "account_move_request_exception.action_account_move_request_exception_confirm"
        )
        return action

