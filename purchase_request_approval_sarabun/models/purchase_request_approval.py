# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class PurchaseRequestApproval(models.Model):
    _inherit = ["purchase.request.approval", "sarabun.document.mixin"]

    main_sarabun_document_id = fields.Many2one(
        comodel_name="sarabun.document",
        string="Main Sarabun Document",
        copy=False,
    )

    state = fields.Selection(
        selection_add=[
            ("sarabun_returned", "Sarabun Returned"),
            ("pending_pr", "Pending PR Revision"),
        ],
        ondelete={
            "sarabun_returned": "set default",
            "pending_pr": "set default",
        },
    )

    def _get_editable_states(self):
        return super()._get_editable_states() + ("sarabun_returned",)

    def button_approved(self):
        for rec in self:
            document = rec.active_sarabun_document_id
            if document and document.is_circulating:
                raise UserError(
                    _("Cannot manually approve while the หนังสือ is still circulating. "
                      "Please wait for the routing to complete or recall the Sarabun document.")
                )
        return super().button_approved()

    def action_open_return_cancel_wizard(self):
        """Open the ตีกลับ/แก้ไข wizard from PA draft — collects the mandatory
        reason before parking PA in ``pending_pr`` and resetting PR + sarabun."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("ตีกลับ/แก้ไข พจ.1"),
            "res_model": "purchase.request.approval.return.cancel.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_approval_id": self.id},
        }

    def _cancel_request_sarabun(self, reason):
        """Cancel the PR's active sarabun.document (state=cancelled) so it
        stops counting as live. The document, its register number, and the
        completed routing chain are ALL retained on the record — the user
        will later click ``action_resume_returned_sarabun`` on the PR to
        revive it back to draft and re-send.

        This is a soft-void — no ``_restart_chain`` yet (the reset happens on
        resume). Runs sudo since ``action_recall``'s guard blocks a signed
        document; this is the origin's escape hatch when พจ.1 rejects the
        approval downstream.
        """
        self.ensure_one()
        pr = self.request_id
        if not pr:
            return
        doc = pr.active_sarabun_document_id
        if not doc or doc.state in ("cancelled", "rejected"):
            return
        doc.sudo().write({"state": "cancelled"})
        doc.message_post(
            body=_(
                "หนังสือถูกยกเลิกเนื่องจาก พจ.1 %(pa)s ถูกส่งกลับให้แก้ไข. "
                "เหตุผล: %(reason)s"
            ) % {"pa": self.name, "reason": reason},
            subtype_xmlid="mail.mt_note",
        )

    def _action_return_for_revision(self, reason):
        """ตีกลับ/แก้ไข — send PA back to พ.1 for revision, keeping the พจ.1
        number for reuse.

        - PA → ``pending_pr`` (name preserved; ``_transition_after_sarabun_approve``
          flips it back to ``draft`` when the fresh sarabun re-completes).
        - PR → ``to_verify`` (budget commitment stays intact; ตีกลับ = back to
          ธุรการ for a fresh look before it goes to budget and out again).
        - PR's active sarabun is CANCELLED (state=cancelled) so it no longer
          counts as live. The user then explicitly clicks
          ``action_resume_returned_sarabun`` on the PR to revive it — that
          two-step ceremony is intentional (no auto-magic revival on close).
        - Redirect the user to the PR form so they can act immediately.
        """
        self.ensure_one()
        pa_body = _(
            "ตีกลับ พจ.1 %(pa)s (เก็บเลข) เหตุผล: %(reason)s"
        ) % {"pa": self.name, "reason": reason}
        self.message_post(body=pa_body, subtype_xmlid="mail.mt_note")
        pr_body = _(
            "พจ.1 %(pa)s ถูกส่งกลับให้แก้ไข. เหตุผล: %(reason)s"
        ) % {"pa": self.name, "reason": reason}
        self.request_id.message_post(body=pr_body, subtype_xmlid="mail.mt_note")
        self._cancel_request_sarabun(reason)
        self.request_id.write({"state": "to_verify"})
        self.write({"state": "pending_pr"})
        return self._redirect_to_request()

    def _redirect_to_request(self):
        """Return an action that opens this PA's linked PR (พ.1) so the user
        lands on the record they need to edit after a return."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "purchase.request",
            "res_id": self.request_id.id,
            "view_mode": "form",
            "target": "current",
        }

    # === Sarabun Document Integration ===

    def _get_sarabun_subject(self):
        return self.title or self.name

    def _sarabun_submit_guard(self):
        self.ensure_one()
        if not self.partner_id:
            raise UserError(_("กรุณาระบุผู้ขาย (Vendor) ก่อนส่งเข้าสารบรรณ"))
        return super()._sarabun_submit_guard()

    def _get_sarabun_sender_department(self):
        return self.requesting_department_id or super()._get_sarabun_sender_department()

    def _on_sarabun_circulating(self, document):
        # Explicit override: flip the PA to 'to_approve' on send. Do NOT call
        # button_to_approve here — that also renders the PDF. The state write
        # is picked up by write() above and mints the พจ.1 number pinned to
        # the fiscal year.
        self.write({"state": "to_approve"})
        return super()._on_sarabun_circulating(document)

    def _on_sarabun_completed(self, document):
        # Routing completed → auto-approve the PA.
        self.button_approved()
        return super()._on_sarabun_completed(document)

    def _on_sarabun_rejected(self, document, step):
        reason = _("ปฏิเสธผ่านสารบรรณ: %s") % (step.note or document.name)
        self._action_do_reject(reason)
        return super()._on_sarabun_rejected(document, step)

    def _on_sarabun_returned(self, document, step):
        self.write({"state": "sarabun_returned"})
        return super()._on_sarabun_returned(document, step)

    def action_resend_to_sarabun(self):
        self.ensure_one()
        document = self.active_sarabun_document_id
        if not document:
            raise UserError(_("No active Sarabun document to resend."))
        return document.action_send()

    def _on_sarabun_cancelled(self, document):
        # ยกเลิกการส่ง Sarabun (terminal) → same effect as manual cancel wizard:
        # cascade cancel to PA + PR, and release the PR's budget commitment.
        reason = _("ยกเลิกการส่งหนังสือ %s") % document.name
        self._action_do_cancel(reason)
        pr = self.request_id
        if pr and pr.budget_commitment_id:
            try:
                pr._cancel_budget_commitment()
                pr.message_post(
                    body=_("Budget commitment %s has been cancelled")
                    % pr.budget_commitment_id.name
                )
            except UserError as e:
                pr.message_post(
                    body=_("Warning: Could not cancel budget commitment: %s")
                    % str(e)
                )
        return super()._on_sarabun_cancelled(document)

    # ADR-0015: render through Sarabun's own no-source layout (สารบรรณ owns the
    # header — เลขที่/หน่วยงาน/เรียน/วันที่ — and the endorsement block). We
    # therefore DON'T override _get_sarabun_report_action (mixin default →
    # False), and instead contribute the live tables (items / budget /
    # committee) via _get_sarabun_body_template — mirroring purchase.request.

    def _get_sarabun_document_type(self):
        return self.env.ref(
            "purchase_request_approval_sarabun.document_type_purchase_request_approval",
            raise_if_not_found=False,
        ) or super()._get_sarabun_document_type()

    def _get_sarabun_body_template(self):
        """The live body — items table, budget details, committee appointments —
        rendered between the หนังสือ's เนื้อหา and its signatures (ADR-0015)."""
        return "purchase_request_approval.report_purchase_request_approval_body"
