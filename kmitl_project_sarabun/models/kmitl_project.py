# -*- coding: utf-8 -*-
from odoo import _, models


class KmitlProject(models.Model):
    """Route a kmitl.project for approval (ขออนุมัติจัดโครงการและค่าใช้จ่าย) through
    e-Saraban. The project owns the state machine (kmitl_project); this bridge only
    wires the หนังสือ: it creates the Document at ``to_send`` and maps the หนังสือ
    outcome back onto the project state (ADR-0002, mirroring agx_approval_sarabun).
    """

    _name = "kmitl.project"
    _inherit = ["kmitl.project", "sarabun.document.mixin"]

    def _get_sarabun_subject(self):
        # เรื่อง of the หนังสือ.
        return _("ขออนุมัติจัดโครงการและค่าใช้จ่าย: %s") % (self.key or self.name)

    def _sarabun_submit_guard(self):
        # A project may raise its หนังสือ only once its budget is reserved
        # (``to_send``). A ตีกลับ/ดึงกลับ หนังสือ is re-sent from the Document
        # itself (still live/returned), not created anew — hence to_send only.
        self.ensure_one()
        return self.state == "to_send"

    # -- Sarabun outcome → project state ----------------------------------
    def _on_sarabun_circulating(self, document):
        # หนังสือเริ่มเวียนลงนาม → "ส่งขออนุมัติแล้ว". Also covers re-sending a
        # หนังสือ that was ตีกลับ/ดึงกลับ (returned → sent).
        if self.state in ("to_send", "returned"):
            # Editing in returned may have changed budget_amount / dimensions —
            # realign the reservation before the หนังสือ goes back out (ADR-0002).
            if self.state == "returned":
                self._resync_project_commitment()
            self.state = "sent"
        return super()._on_sarabun_circulating(document)

    def _on_sarabun_completed(self, document):
        # หนังสือลงนามครบ → อนุมัติแล้ว = เริ่มดำเนินการทันที (ADR-0002: no idle
        # "approved" state — the project may raise purchase requests / เบิกจ่าย now).
        self.state = "in_progress"
        return super()._on_sarabun_completed(document)

    def _on_sarabun_returned(self, document, step):
        # ตีกลับ / ดึงกลับ: กลับสู่ ``returned`` — คงงบ, แก้ได้ทุกฟิลด์ แล้วส่ง
        # หนังสือใหม่ (recall forwards here by the mixin default, step empty).
        self.state = "returned"
        return super()._on_sarabun_returned(document, step)

    def _on_sarabun_rejected(self, document, step):
        # ปฏิเสธ (terminal): land in ``rejected`` and release the reservation.
        self.action_reject()
        return super()._on_sarabun_rejected(document, step)

    def _on_sarabun_cancelled(self, document):
        # ยกเลิกการส่ง: only the send is voided — fall back to ``to_send`` keeping
        # the reservation, ready for a fresh หนังสือ.
        self.state = "to_send"
        return super()._on_sarabun_cancelled(document)

    def _get_sarabun_report_action(self):
        # Do NOT delegate the official หนังสือ PDF to the project's own report yet:
        # kmitl_project.report_kmitl_project is an unfinished stub (body commented
        # out) and — unlike a proper delegated report — does not t-call the หนังสือ
        # endorsement/signature block at its tail, so a signed copy would show no
        # signatures. Returning False makes the หนังสือ use the complete default
        # sarabun document report. Re-enable (return the report action) once a real
        # แบบเสนอโครงการ report is built. See ADR-0002.
        return False

    # -- Discard the stale หนังสือ when abandoning the approval ------------
    def _abandon_stale_sarabun_documents(self):
        """Discard any un-numbered หนังสือ (a draft not yet sent, or one ตีกลับ/
        ดึงกลับ for revision) still attached when the project is reset to draft or
        cancelled — otherwise ``sarabun_has_live_document`` keeps blocking a fresh
        submission. Completed (numbered, signed) and terminal docs are audit
        records and are kept; only ``draft``/``returned`` docs — which never
        consumed a register number — are removed (unlink cascades their routing
        steps). The engine offers no withdraw for a non-circulating doc, so an
        unlink is the supported discard here."""
        for project in self:
            stale = project.sarabun_document_ids.filtered(
                lambda d: d.state in ("draft", "returned")
            )
            if stale:
                stale.sudo().unlink()

    def action_draft(self):
        res = super().action_draft()
        self._abandon_stale_sarabun_documents()
        return res

    def action_cancel(self):
        res = super().action_cancel()
        self._abandon_stale_sarabun_documents()
        return res
