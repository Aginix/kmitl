# -*- coding: utf-8 -*-
from odoo import _, api, models


class ApprovalRequest(models.Model):
    _name = "approval.request"
    _inherit = [
        "approval.request",
        "sarabun.document.mixin",
        "portal.mixin",
        "thai.date.mixin",
    ]

    def _compute_access_url(self):
        """Compute the access URL for portal access."""
        super()._compute_access_url()
        for request in self:
            request.access_url = f"/my/approval_request/{request.id}"

    def _get_report_base_filename(self):
        self.ensure_one()
        return "Approval Request-%s" % (self.name)

    def open_preview(self):
        if self.id:
            return {
                "type": "ir.actions.act_url",
                "url": self.access_url,
                "target": "new",
            }

    def _get_sarabun_subject(self):
        self.ensure_one()
        return _(
            "ขออนุมัติค่าใช้จ่ายประเภท%(name)s %(src)s ประจำปีงบประมาณ พ.ศ. %(fy)s %(dept)s"
        ) % {
            "name": self.category_id.name,
            "src": self._sarabun_dim_name(self.source_analytic_id),
            "fy": self.account_fiscal_year_id.name or "",
            "dept": self._sarabun_dim_name(self.department_analytic_id),
        }

    @staticmethod
    def _sarabun_dim_name(analytic):
        name = (analytic.complete_name or analytic.name or "") if analytic else ""
        return name.replace(" / ", " ")

    def _sarabun_submit_guard(self):
        # A request may only be routed once its budget is reserved (to_send).
        return self.state == "to_send"

    # -- Sarabun outcome → request state ----------------------------------
    def _on_sarabun_circulating(self, document):
        # หนังสือเริ่มเวียน → คำขออยู่ระหว่างขออนุมัติ. Also covers re-sending a
        # หนังสือ that was returned (ตีกลับ/ดึงกลับ) for revision.
        # State only: the request's own วันที่ส่งคำขอ and ปีงบประมาณ are NOT touched
        # here. The หนังสือ's ลงวันที่ is re-stamped on every (re-)send (ADR-0010) —
        # copying it over would drag the request's ปีงบ along with it, away from the
        # year its ใบจอง was reserved in. The letter's date lives on the letter.
        if self.state in ("to_send", "returned"):
            self.state = "sent"
        return super()._on_sarabun_circulating(document)

    def _on_sarabun_completed(self, document):
        # อนุมัติ → คำขอได้รับอนุมัติแล้ว. สถานะ approved คือช่วงบันทึกผลค่าใช้จ่ายจริง
        # ในตัว (is_actual_editable) — ผู้สร้างกรอกได้เลยทันที ไม่มีปุ่มคั่น
        self.state = "approved"
        return super()._on_sarabun_completed(document)

    def _on_sarabun_rejected(self, document, step):
        # ปฏิเสธ (terminal): action_cancel lands the request in ``rejected`` and
        # releases the budget commitment.
        self.action_cancel()
        return super()._on_sarabun_rejected(document, step)

    def _on_sarabun_returned(self, document, step):
        # ตีกลับ / ดึงกลับ: land in ``returned`` — editable everywhere except the
        # budget (see _compute_is_plan_editable), then the หนังสือ is re-sent.
        self.state = "returned"
        return super()._on_sarabun_returned(document, step)

    def _on_sarabun_cancelled(self, document):
        # ยกเลิกการส่ง: only the send is voided (register number cancelled) — fall
        # back to ``to_send`` keeping the reservation, ready for a fresh หนังสือ.
        self.state = "to_send"
        return super()._on_sarabun_cancelled(document)

    @api.depends("state", "sarabun_state")
    def _compute_is_plan_editable(self):
        """A Sarabun-returned request reopens the whole plan for editing (except
        budget). A disbursement return leaves the หนังสือ ``completed`` and is
        handled as a narrow correction instead — so it stays locked here."""
        super()._compute_is_plan_editable()
        for rec in self:
            if rec.state == "returned" and rec.sarabun_state == "returned":
                rec.is_plan_editable = True

    # ADR-0015: render through Sarabun's own no-source layout (so the หนังสือ reuses
    # สารบรรณ's header — เลขที่/หน่วยงาน/เรียน/วันที่/อ้างถึง — and its endorsement
    # block) rather than delegating to the standalone approval report. We therefore
    # DON'T override _get_sarabun_report_action (mixin default → False), and instead:
    #   - seed the editable เนื้อหา (บรรยาย) once, and
    #   - contribute the live budget/expense tables as the origin body fragment.

    def _get_sarabun_body_template(self):
        """The live budget/expense body, rendered between the หนังสือ's เนื้อหา and
        its signatures (ADR-0015). Kept live — never editable — so the official
        หนังสือ can never show numbers that diverge from the reserved commitment or
        the disbursement it feeds."""
        return "agx_approval.report_approval_request_body"

    def _get_sarabun_content(self):
        """The editable บรรยาย seeding เนื้อหา (policy 5A: seeded once at submit,
        then owned by the user — no auto-regenerate; the edit window is the
        หนังสือ's draft/returned states). The authoritative tables are NOT seeded
        here — they render live via _get_sarabun_body_template."""
        self.ensure_one()
        return self.env["ir.qweb"]._render(
            "agx_approval.report_approval_request_narrative",
            {"o": self.with_context(lang="th_TH")},
        )

    def action_submit_to_sarabun(self):
        """Also carry the request's เอกสารแนบ onto the หนังสือ as สิ่งที่ส่งมาด้วย."""
        action = super().action_submit_to_sarabun()
        if action and action.get("res_id"):
            document = self.env["sarabun.document"].browse(action["res_id"])
            self._copy_attachments_to_sarabun(document)
        return action

    def _copy_attachments_to_sarabun(self, document):
        """Copy the request's attachments onto the หนังสือ as enclosures. Copied
        (not merely referenced) with ``res_model=sarabun.document`` so a Route
        recipient without rights on the request can still open them — the หนังสือ's
        ACL governs (same ownership choice as budget_transfer_sarabun). Seeded once
        at submit; the drafter then manages enclosures on the หนังสือ itself."""
        self.ensure_one()
        enclosures = self.env["ir.attachment"]
        for attachment in self.attachment_ids:
            enclosures |= attachment.sudo().copy(
                {"res_model": "sarabun.document", "res_id": document.id}
            )
        if enclosures:
            document.sudo().write(
                {"enclosure_attachment_ids": [(4, a.id) for a in enclosures]}
            )
