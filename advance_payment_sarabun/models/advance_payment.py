# -*- coding: utf-8 -*-
from markupsafe import escape

from odoo import _, models


class AdvancePayment(models.Model):
    """Route an advance.payment approval (to_approve) through e-Saraban. The
    loan owns the state machine (advance_payment); this bridge only wires the
    หนังสือ: it creates the Document at ``to_approve`` and maps the หนังสือ
    outcome back onto the loan state (ADR-0011, mirroring kmitl_project_sarabun
    / agx_approval_sarabun)."""

    _name = "advance.payment"
    _inherit = ["advance.payment", "sarabun.document.mixin"]

    def _get_sarabun_subject(self):
        self.ensure_one()
        return _("ขออนุมัติสัญญายืมเงิน %s") % (self.name or "")

    def _get_sarabun_addressee(self):
        self.ensure_one()
        return _("เจ้าหน้าที่งานเงินยืม")

    def _get_sarabun_content(self):
        """เนื้อหา (บันทึกนำ) — ผู้ยืม จำนวนเงิน และเหตุผลการยืม."""
        self.ensure_one()
        body = _(
            "ด้วย %(borrower)s มีความประสงค์ขอยืมเงินทดรองจ่าย จำนวน"
            " %(amount)s %(currency)s เพื่อ%(reason)s"
        ) % {
            "borrower": escape(self.requested_by.name or ""),
            "amount": "{:,.2f}".format(self.loan_amount),
            "currency": escape(self.currency_id.name or ""),
            "reason": escape(self.loan_reason or ""),
        }
        return "<p>%s</p>" % body

    def _get_sarabun_document_type(self):
        return self.env.ref(
            "advance_payment_sarabun.document_type_advance_payment",
            raise_if_not_found=False,
        )

    def _sarabun_submit_guard(self):
        # A loan may raise its หนังสือ only while awaiting approval. A
        # ตีกลับ/ดึงกลับ หนังสือ is re-sent from the Document itself (still
        # live/returned), not created anew.
        self.ensure_one()
        return self.state == "to_approve"

    # -- submit: seed เรียน (addressee) on the fresh หนังสือ ------------------
    def action_submit_to_sarabun(self):
        action = super().action_submit_to_sarabun()
        if action and action.get("res_id"):
            document = self.env["sarabun.document"].browse(action["res_id"])
            document.sudo().write({"addressee": self._get_sarabun_addressee()})
        return action

    # -- Sarabun outcome → loan state ---------------------------------------
    def _on_sarabun_completed(self, document):
        # หนังสือลงนามครบ → อนุมัติ: reuse the base action_approve() — it
        # creates the disbursement account.payment and moves the loan to
        # waiting_transfer — unchanged, since the loan is still at to_approve.
        self.action_approve()
        return super()._on_sarabun_completed(document)

    def _on_sarabun_returned(self, document, step):
        # ตีกลับ: back to to_verify so the finance officer can revise, then
        # re-verify and re-send.
        self.state = "to_verify"
        return super()._on_sarabun_returned(document, step)

    def _on_sarabun_rejected(self, document, step):
        # ปฏิเสธ (terminal): cancel the agreement with the approver's reason.
        # No payment exists yet at to_approve, so nothing to void.
        reason = (step and step.note) or _("ปฏิเสธผ่านระบบสารบรรณ")
        self._action_do_cancel(reason)
        return super()._on_sarabun_rejected(document, step)

    def _on_sarabun_cancelled(self, document):
        # ยกเลิกการส่ง: only the send is voided — the loan stays at
        # to_approve, ready for a fresh หนังสือ.
        return super()._on_sarabun_cancelled(document)

    def _on_sarabun_recalled(self, document):
        # ดึงกลับ must NOT delegate to the mixin's default (→ returned): the
        # loan stays at to_approve, re-sendable (locked negative-outcome
        # mapping, ADR-0011) — note only.
        self.message_post(
            body=_("ดึงหนังสือกลับเพื่อแก้ไข: %s") % document.name,
            subtype_xmlid="mail.mt_note",
        )
