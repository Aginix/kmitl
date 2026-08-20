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
            summary=_("หนังสือดำเนินการเสร็จสิ้นแล้ว"),
            user_id=creator.id,
        )
