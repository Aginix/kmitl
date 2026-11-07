from markupsafe import Markup

from odoo import _, models


class SarabunDocument(models.Model):
    _inherit = "sarabun.document"

    def _complete_document(self):
        """Ping the creator when the หนังสือ reaches เสร็จสิ้น.

        agx_sarabun core is Todo-agnostic and clears every routing Todo at
        completion (§7.2). The owner of the เรื่อง (``sender_user_id`` — the
        original creator, never copied) is usually no longer a routing holder by
        then, so nothing tells them their letter is done. This bridge owns the Todo
        integration, so it schedules one acknowledgement Todo for that creator — the
        outcome lands in their unified inbox and clears by Mark as Read.

        Only when the state actually transitions to ``completed`` (core no-ops when
        already terminal), so a re-completion after ตีกลับ notifies once per finish.
        """
        was_circulating = self.state == "circulating"
        res = super()._complete_document()
        if was_circulating and self.state == "completed":
            self._notify_creator_completed()
        return res

    def _notify_creator_completed(self):
        self.ensure_one()
        creator = self.sender_user_id
        xmlid = "agx_sarabun_todo.mail_activity_sarabun_completed"
        if not creator or not self.env.ref(xmlid, raise_if_not_found=False):
            return
        self.activity_schedule(
            act_type_xmlid=xmlid,
            summary=self._activity_subject() or _("หนังสือดำเนินการเสร็จสิ้นแล้ว"),
            note=Markup("<p>%s</p>") % _("หนังสือดำเนินการเสร็จสิ้นแล้ว"),
            user_id=creator.id,
        )

    def _do_return(self, step, destination="sender_restart", resume_step_id=None):
        """Tell the creator their หนังสือ was ตีกลับ — core only logs an internal
        note, so nothing reaches them otherwise."""
        res = super()._do_return(
            step, destination=destination, resume_step_id=resume_step_id
        )
        self._notify_creator_returned(step)
        return res

    def _notify_creator_returned(self, step):
        self.ensure_one()
        creator = self.sender_user_id
        xmlid = "agx_sarabun_todo.mail_activity_sarabun_returned"
        if not creator or not self.env.ref(xmlid, raise_if_not_found=False):
            return
        note = _(
            "หนังสือถูกตีกลับโดย %(who)s — เหตุผล: %(reason)s",
            who=step.acted_by_id.name or "",
            reason=step.note or "-",
        )
        self.activity_schedule(
            act_type_xmlid=xmlid,
            summary=self._activity_subject() or _("หนังสือถูกตีกลับ"),
            note=Markup("<p>%s</p>") % note,
            user_id=creator.id,
        )

    def write(self, vals):
        """Leaving ตีกลับ (re-send, Reset to draft, …) is the creator acting on the
        ตีกลับ Todo — close it (Execution: never by Mark as Read)."""
        returned = self.browse()
        if vals.get("state", "returned") != "returned":
            returned = self.filtered(lambda d: d.state == "returned")
        res = super().write(vals)
        returned_type = returned and self.env.ref(
            "agx_sarabun_todo.mail_activity_sarabun_returned", raise_if_not_found=False
        )
        if returned_type:
            self.env["mail.activity"].sudo().search(
                [
                    ("res_model", "=", self._name),
                    ("res_id", "in", returned.ids),
                    ("activity_type_id", "=", returned_type.id),
                ]
            ).action_done()
        return res
