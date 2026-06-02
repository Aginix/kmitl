# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class BudgetCommitment(models.Model):
    _inherit = 'budget.commitment'

    READONLY_STATES = {
        "reserved": [("readonly", True)],
        "partial": [("readonly", True)],
        "done": [("readonly", True)],
        "cancel": [("readonly", True)],
    }

    procurement_plan_id = fields.Many2one(
        comodel_name="procurement.plan",
        states=READONLY_STATES,
    )

    def _sync_state(self):
        """When a plan's commitment is fully consumed it reaches ``done``;
        propagate that to the owning procurement plan so it auto-closes once
        every installment has been disbursed (ADR-0005 / done-when-consumed)."""
        super()._sync_state()
        for commitment in self.filtered(
            lambda c: c.state == "done" and c.procurement_plan_id
        ):
            plan = commitment.procurement_plan_id
            if plan.state == "in_progress":
                plan.action_done()

    def action_view_procurement_plan(self):
        self.ensure_one()
        if not self.procurement_plan_id:
            return {"type": "ir.actions.act_window_close"}

        return {
            "type": "ir.actions.act_window",
            "res_model": "procurement.plan",
            "view_mode": "form",
            "res_id": self.procurement_plan_id.id,
            "target": "current",
        }

