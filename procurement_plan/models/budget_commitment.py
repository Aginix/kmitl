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

    @api.onchange("procurement_plan_analytic_id")
    def _onchange_procurement_plan_analytic_id(self):
        """Keep ``procurement_plan_id`` in step with the แผนจัดซื้อจัดจ้าง
        analytic dimension: when the analytic account changes, point the record
        link at the plan owning that account (cleared when no plan matches)."""
        account = self.procurement_plan_analytic_id
        self.procurement_plan_id = (
            self.env["procurement.plan"].search(
                [("analytic_account_id", "=", account.id)], limit=1
            )
            if account
            else False
        )

    def _sync_state(self):
        """When a plan's commitment is fully consumed it reaches ``done``;
        propagate that to the owning procurement plan so it auto-closes once
        every installment has been disbursed (ADR-0005 / done-when-consumed).

        A leftover-return (ส่งคืนเงินเหลือจ่าย / คืนจอง) also drives the
        commitment to ``done``, but it must NOT auto-close the plan: returning
        unspent budget is a financial action, while closing the plan stays a
        manual procurement step (ADR-0009). The return flow posts its line under
        ``skip_plan_autoclose`` so only that path is exempted; ordinary
        full-consumption still closes the plan as before."""
        super()._sync_state()
        if self.env.context.get("skip_plan_autoclose"):
            return
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

