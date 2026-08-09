from odoo import models

RESERVE_BUDGET_ACTIVITY = (
    "purchase_request_todo_role_unit.mail_activity_pr_reserve_budget"
)
BUDGET_COMMITMENT_ROLE = "budget_role.role_budget_commitment"


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    def _schedule_reserve_budget_todo(self):
        """Raise the execution Todo when the พ.1 enters รอจองงบประมาณ. Route
        to the จองงบประมาณ role of the พ.1's operating unit (role-in-unit,
        ADR-0002); if role or OU is missing, fall back to a personal Todo on
        ``requested_by`` so the flow never stalls silently."""
        act_type = self.env.ref(RESERVE_BUDGET_ACTIVITY, raise_if_not_found=False)
        role = self.env.ref(BUDGET_COMMITMENT_ROLE, raise_if_not_found=False)
        if not act_type:
            return
        for rec in self:
            if rec.activity_ids.filtered(lambda a: a.activity_type_id == act_type):
                continue  # already raised
            if role and rec.operating_unit_id:
                rec.activity_schedule(
                    RESERVE_BUDGET_ACTIVITY,
                    responsible_role_id=role.id,
                    operating_unit_id=rec.operating_unit_id.id,
                )
            elif rec.requested_by:
                rec.activity_schedule(
                    RESERVE_BUDGET_ACTIVITY,
                    user_id=rec.requested_by.id,
                )

    def button_to_verify(self):
        res = super().button_to_verify()
        self._schedule_reserve_budget_todo()
        return res

    def button_to_submit(self):
        res = super().button_to_submit()
        # Genuine completion of the reservation step: log it to Completed history.
        self.activity_feedback([RESERVE_BUDGET_ACTIVITY])
        return res

    def button_draft(self):
        res = super().button_draft()
        # Reset — the reservation was not done; drop without a history row.
        self.activity_unlink([RESERVE_BUDGET_ACTIVITY])
        return res

    def _action_do_cancel(self, reason):
        res = super()._action_do_cancel(reason)
        self.activity_unlink([RESERVE_BUDGET_ACTIVITY])
        return res
