# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    can_resume_returned_sarabun = fields.Boolean(
        compute="_compute_can_resume_returned_sarabun",
        help="True when this PR has a PA parked in pending_pr and a cancelled "
        "sarabun ready to be revived — drives the 'ส่งเรื่องสารบรรณ' button "
        "visibility for the two-step ตีกลับ/แก้ไข resume flow.",
    )

    @api.depends(
        "state",
        "request_approval_ids.state",
        "sarabun_document_ids.state",
    )
    def _compute_can_resume_returned_sarabun(self):
        for rec in self:
            rec.can_resume_returned_sarabun = (
                rec.state == "to_approve"
                and any(
                    pa.state == "pending_pr" for pa in rec.request_approval_ids
                )
                and any(
                    doc.state == "cancelled" for doc in rec.sarabun_document_ids
                )
            )

    def action_submit_to_sarabun(self):
        """Override the Create Sarabun entry point: when this PR came from a
        ตีกลับ/แก้ไข flow (PA in pending_pr + cancelled sarabun on file),
        revive the cancelled หนังสือ back to draft (reusing the same document
        and register number) instead of spawning a new one. Otherwise fall
        through to the standard mixin behaviour that creates a fresh sarabun."""
        self.ensure_one()
        if self.can_resume_returned_sarabun:
            return self._resume_returned_sarabun()
        return super().action_submit_to_sarabun()

    def _resume_returned_sarabun(self):
        """Revive the latest cancelled sarabun on this PR back to editable
        ``draft`` (same document + register number) and re-sync the
        origin-driven fields (``subject`` / ``sender_department_id``) from the
        current PR — so if the user edited PR.title while it was returned to
        draft, the หนังสือ picks up the new subject on resume. Called from
        :meth:`action_submit_to_sarabun` when the two-step ตีกลับ/แก้ไข resume
        conditions are met."""
        self.ensure_one()
        doc = self.env["sarabun.document"].search(
            [
                ("origin_model", "=", self._name),
                ("origin_res_id", "=", self.id),
                ("state", "=", "cancelled"),
            ],
            order="id desc",
            limit=1,
        )
        if not doc:
            raise UserError(_("ไม่พบหนังสือที่ถูกยกเลิกไว้"))
        doc = doc.sudo()
        doc.routing_step_ids._clear_activities()
        doc._restart_chain()
        resume_vals = {"state": "draft", "subject": self._get_sarabun_subject()}
        dept = self._get_sarabun_sender_department()
        if dept:
            resume_vals["sender_department_id"] = dept.id
        doc.write(resume_vals)
        doc.message_post(
            body=_(
                "หนังสือถูกนำกลับมาใช้ใหม่จากใบเดิมที่ถูกยกเลิก และ sync "
                "ค่าจาก พ.1 (subject, sender department)"
            ),
            subtype_xmlid="mail.mt_note",
        )
        return {
            "type": "ir.actions.act_window",
            "res_model": "sarabun.document",
            "res_id": doc.id,
            "view_mode": "form",
            "target": "current",
        }

    def _transition_after_sarabun_approve(self):
        for rec in self:
            if not rec.is_egp:
                rec._apply_sarabun_approve_metadata()
                rec.write({"state": "in_approval"})
                # keep-number return parks the PA in ``pending_pr`` — reuse it
                # (same พจ.1 number) instead of raising "already been created",
                # and flip it back to draft now that the new PR sarabun has
                # been approved. Re-sync copied fields from the (edited) PR
                # so the PA reflects the revised data, not the stale snapshot
                # taken at initial creation.
                existing = self.env["purchase.request.approval"].search(
                    [("request_id", "=", rec.id), ("state", "!=", "cancelled")],
                    limit=1,
                )
                if existing:
                    if existing.state == "pending_pr":
                        vals = rec._prepare_approval_sync_vals()
                        vals["state"] = "draft"
                        existing.write(vals)
                else:
                    rec.button_create_approval()
            else:
                super(PurchaseRequest, rec)._transition_after_sarabun_approve()

    def _prepare_approval_sync_vals(self):
        """Vals to re-sync an EXISTING PA record from this PR — used when a
        ตีกลับ/แก้ไข PA (parked in ``pending_pr``) is revived after the PR was
        edited. Copies the same field set as ``_prepare_approval_vals`` but
        omits identity/immutable fields (``request_id``, ``date_start``,
        ``origin``, ``state``, ``validation_status``) and resets the PA's own
        lines to mirror the PR lines (clear then create)."""
        vals = self._prepare_approval_vals()
        for key in ("request_id", "date_start", "origin", "state", "validation_status"):
            vals.pop(key, None)
        vals["line_ids"] = [(5, 0, 0)] + vals.get("line_ids", [])
        return vals
