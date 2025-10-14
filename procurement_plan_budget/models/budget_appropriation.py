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
        super().action_post()
        self._log_message_on_linked_documents()

    def _log_message_on_linked_documents(self):
        for line in self.line_ids:
            if line.procurement_plan_id:
                self.message_post(
                    body=line._message_link_to_procurement_plan(),
                    message_type="comment",
                )

                line.procurement_plan_id.message_post(
                    body=line._message_link_back_from_procurement_plan(),
                    message_type="comment",
                )

    def _get_record_url(self):
        return "/web#id={}&model={}&view_type=form".format(
            self.id, self._name
        )
