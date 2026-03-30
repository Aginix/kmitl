# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class KmitlProject(models.Model):
    _name = "kmitl.project"
    _order = "main_exception_id asc, id desc"
    _inherit = ["kmitl.project", "base.exception"]

    @api.model
    def test_all_draft_orders(self):
        order_set = self.search([("state", "=", "draft")])
        order_set.detect_exceptions()
        return True

    @api.model
    def _reverse_field(self):
        return "kmitl_project_ids"

    def button_draft(self):
        res = super().button_draft()
        for request in self:
            request.exception_ids = False
            request.main_exception_id = False
            request.ignore_exception = False
        return res

    def button_confirm(self):
        if self.detect_exceptions() and not self.ignore_exception:
            return self._popup_exceptions()
        self.write({"approval_state": "submitted"})

    @api.model
    def _get_popup_action(self):
        action = self.env.ref("kmitl_project.action_kmitl_project_exception_confirm")
        return action
