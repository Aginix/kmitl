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
        procurement_lines = self.line_ids.filtered(lambda l: l.procurement_plan_id)
        if not procurement_lines:
            return

        # Post a single consolidated message on budget.appropriation
        body_parts = []
        for line in procurement_lines:
            body_parts.append(line._message_link_to_procurement_plan())

        if body_parts:
            self.message_post(
                body="<br/>".join(body_parts),
                message_type="comment",
            )

        # Post individual messages on each procurement.plan
        for line in procurement_lines:
            line.procurement_plan_id.message_post(
                body=line._message_link_back_from_procurement_plan(),
                message_type="comment",
            )

    def _get_record_url(self):
        return "/web#id={}&model={}&view_type=form".format(
            self.id, self._name
        )
