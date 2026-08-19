# -*- coding: utf-8 -*-
import logging

from odoo import Command, models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class BudgetAppropriation(models.Model):
    _inherit = "budget.appropriation"

    procurement_plan_ids = fields.One2many(
        "budget.appropriation.line",
        compute="_compute_procurement_plan_ids",
        store=False,
        readonly=True,
    )

    @api.depends("line_ids.enable_procurement_plan", "line_ids.procurement_plan_amount", "line_ids.procurement_plan_unit", "line_ids.procurement_plan_id")
    def _compute_procurement_plan_ids(self):
        for record in self:
            line_ids = record.line_ids.filtered(lambda x: x.enable_procurement_plan)
            record.procurement_plan_ids = line_ids

    def action_review(self):
        super().action_review()

    def action_post(self):
        super().action_post()
        self._reserve_procurement_plans()
        self._log_message_on_linked_documents()

    def _reserve_procurement_plans(self):
        """Reserve each created procurement plan's budget the moment the
        appropriation is posted. super().action_post() has already posted the
        appropriation move, so the pool is available to lock. Drives the plan
        through its own to_verify → verified transition — reserving is the
        budget layer's ``_on_verify`` hook, not reimplemented here — so it lands
        at ``verified`` in this single transaction."""
        for line in self.line_ids.filtered(lambda l: l.procurement_plan_id):
            line.procurement_plan_id.action_verify()

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
        return "/web#id={}&model={}&view_type=form".format(self.id, self._name)
