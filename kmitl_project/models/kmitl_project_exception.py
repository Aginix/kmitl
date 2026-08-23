# -*- coding: utf-8 -*-
import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class KmitlProject(models.Model):
    _name = "kmitl.project"
    _inherit = ["kmitl.project", "base.exception"]
    # Deliberately does NOT take the OCA "main_exception_id asc, id desc" _order:
    # projects stay newest-first as everywhere else in the module — an exception
    # surfaces on the form and in the blocking wizard, not by reordering lists.

    @api.model
    def test_all_draft_orders(self):
        order_set = self.search([("state", "=", "draft")])
        order_set.detect_exceptions()
        return True

    @api.model
    def _reverse_field(self):
        return "kmitl_project_ids"

    def action_draft(self):
        res = super().action_draft()
        for request in self:
            request.exception_ids = False
            request.main_exception_id = False
            request.ignore_exception = False
        return res

    def action_confirm(self):
        if self.detect_exceptions() and not self.ignore_exception:
            return self._popup_exceptions()
        return super().action_confirm()

    @api.model
    def _get_popup_action(self):
        action = self.env.ref("kmitl_project.action_kmitl_project_exception_confirm")
        return action
