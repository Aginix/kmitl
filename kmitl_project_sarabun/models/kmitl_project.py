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
        # Render the หนังสือ PDF from the project's own report.
        return self.env.ref("kmitl_project.action_report_kmitl_project")
