# -*- coding: utf-8 -*-
import logging

from odoo import Command, models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class BudgetAppropriation(models.Model):
    _inherit = "budget.appropriation"

    def action_review(self):
        super().action_review()

    def action_post(self):
        # Need to invoke the `_create_procurement_plan` before action_post
        self._create_procurement_plan()
        self._log_message_on_linked_documents()

        super().action_post()

    def _create_procurement_plan(self):
        for line in self.line_ids:
            if line.enable_procurement_plan:
                line._create_procurement_plan()

    def _log_message_on_linked_documents(self):
        for line in self.line_ids:
            if line.procurement_plan_id:
                self.message_post(
                    body=line._message_link_to_procurement_plan(),
                    message_type="notification",
                )

                line.procurement_plan_id.message_post(
                    body=line._message_link_back_from_procurement_plan(),
                    message_type="notification",
                )

    def _get_record_url(self):
        return "/web#id={}&model={}&view_type=form".format(
            self.id, self._name
        )
