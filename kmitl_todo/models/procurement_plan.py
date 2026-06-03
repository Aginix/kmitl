from odoo import models

PLAN_FILL_ACTIVITY = "kmitl_todo.mail_activity_procurement_plan_fill"
PLAN_OFFICER_ROLE = "kmitl_todo.role_procurement_plan_officer"


class ProcurementPlan(models.Model):
    # Add the activity mixin to procurement.plan (it had only mail.thread).
    _name = "procurement.plan"
    _inherit = ["procurement.plan", "mail.activity.mixin"]

    # ------------------------------------------------------------------
    # UC1 — Execution Todo: fill the operating plan before a พ.1 can be made
    # ------------------------------------------------------------------
    def _schedule_fill_plan_todo(self):
        """Route to the เจ้าหน้าที่แผน role of the plan's operating unit; fall
        back to the plan owner when the unit is unknown (ADR-0002)."""
        act_type = self.env.ref(PLAN_FILL_ACTIVITY, raise_if_not_found=False)
        role = self.env.ref(PLAN_OFFICER_ROLE, raise_if_not_found=False)
        if not act_type:
            return
        for plan in self:
            if plan.activity_ids.filtered(lambda a: a.activity_type_id == act_type):
                continue  # already raised
            if plan.operating_unit_id and role:
                plan.activity_schedule(
                    PLAN_FILL_ACTIVITY,
                    responsible_role_id=role.id,
                    operating_unit_id=plan.operating_unit_id.id,
                )
            else:
                plan.activity_schedule(PLAN_FILL_ACTIVITY, user_id=plan.user_id.id)

    def _clear_fill_plan_todo(self):
        self.activity_feedback([PLAN_FILL_ACTIVITY])

    def action_new(self):
        res = super().action_new()
        self._schedule_fill_plan_todo()
        return res

    def action_ready(self):
        res = super().action_ready()
        self._clear_fill_plan_todo()
        return res

    def action_on_hold(self):
        res = super().action_on_hold()
        self._clear_fill_plan_todo()
        return res

    def action_reset_to_draft(self):
        res = super().action_reset_to_draft()
        self._clear_fill_plan_todo()
        return res
