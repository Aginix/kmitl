# -*- coding: utf-8 -*-
from odoo import api, models


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
        return self.category_id.name

    def _sarabun_submit_guard(self):
        # A request may only be routed once its budget is reserved (submitted).
        return self.state == "submitted"

    # -- Sarabun outcome → request state ----------------------------------
    def _on_sarabun_circulating(self, document):
        # หนังสือเริ่มเวียน → คำขออยู่ระหว่างขออนุมัติ
        if self.state == "submitted":
            self.state = "sent"
        return super()._on_sarabun_circulating(document)

    def _on_sarabun_completed(self, document):
        # อนุมัติ → คำขอได้รับอนุมัติแล้ว
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
        # back to ``submitted`` keeping the reservation, ready for a fresh หนังสือ.
        self.state = "submitted"
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

    def _get_sarabun_report_action(self):
        """Delegate Sarabun report to Approval Request report."""
        return self.env.ref("agx_approval.action_report_approval_request")
