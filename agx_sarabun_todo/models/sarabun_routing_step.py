from odoo import models


class SarabunRoutingStep(models.Model):
    _inherit = "sarabun.routing.step"

    def _stamp(self, actor, note, disposition, signed_as_position=False):
        """Snapshot the actor's own awaiting-action Todo to history before core
        clears it (ADR-0004 + ADR-0014).

        A *stamped* step is one the ``actor`` ACTED on — approved, acknowledged,
        directed, returned or rejected — so from that user's inbox the Todo is
        finished. Core's ``_clear_activities`` (invoked inside ``super()._stamp``)
        drops the activity with a plain ``unlink()``, which never reaches
        ``mail.activity._action_done`` — the only place that snapshots a completed
        Todo into ``todo.log``. Without this hook a signed หนังสือ leaves the inbox
        correctly but never appears under "Completed by me".

        Only the *actor's* copy is logged, attributed to the actor (``with_user``
        so it is right even when the engine acts privileged / on behalf of the
        holder). The other first-to-act holders of the same step never acted
        (someone else did), so their vanishing copies correctly leave no history.
        Pure teardowns — ดึงกลับ, ยกเลิกการส่ง, the ตีกลับ/ปฏิเสธ tail-clear and a
        delegate reassignment — call ``_clear_activities`` directly (never
        ``_stamp``), so they are never mistaken for completions.

        Lives in the bridge, not agx_sarabun core: ``todo.log`` / ``todo_category``
        are mail_activity_todo concepts the Todo-agnostic engine does not know.
        """
        links = (
            self.env["sarabun.routing.step.activity"]
            .sudo()
            .search([("step_id", "in", self.ids), ("user_id", "=", actor.id)])
        )
        activities = links.mapped("activity_id").filtered("todo_category")
        if activities:
            self.env["todo.log"].with_user(actor).sudo()._log_completed(activities)
        return super()._stamp(
            actor, note, disposition, signed_as_position=signed_as_position
        )
