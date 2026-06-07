# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


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

    def _prepare_sarabun_document_vals(self):
        """Prepare values for creating a sarabun document."""
        self.ensure_one()
        vals = super()._prepare_sarabun_document_vals()
        vals["subject"] = self.category_id.name
        return vals

    def _on_sarabun_completed(self, document):
        """Called when sarabun document routing is completed."""
        _logger.info(
            "Sarabun completed callback for Approval Request %s (id=%s) from document %s",
            self.name,
            self.id,
            document.name,
        )
        self.state = "approved"
        self.message_post(
            body=_("Approved via Sarabun document: %s") % document.name,
        )

    def _on_sarabun_rejected(self, document, step):
        """Called when the Sarabun document is rejected (ปฏิเสธ, terminal).

        Reject lands the request in its terminal ``rejected`` state
        (``action_cancel`` sets ``state = "rejected"`` and releases the budget
        commitment). Recall/cancel is handled separately in
        ``_on_sarabun_cancelled``. Runs in the actor's transaction — let any
        error propagate to roll the disposition back.
        """
        self.action_cancel()
        reason = step.note if step and step.note else _("No reason provided")
        self.message_post(
            body=_("Rejected via Sarabun. Reason: %s") % reason,
        )

    def _on_sarabun_returned(self, document, step):
        """Called when the Sarabun document is returned for revision (ตีกลับ).

        Returned is revisable: re-open the request to ``draft`` so the user can
        amend and resubmit. The budget commitment is released by
        ``action_draft``.
        """
        self.action_draft()
        reason = step.note if step and step.note else _("No reason provided")
        self.message_post(
            body=_("Returned via Sarabun for revision. Reason: %s") % reason,
        )

    def _on_sarabun_cancelled(self, document):
        """Called when the Sarabun document is recalled/cancelled (เรียกคืน).

        Re-open the request to ``draft`` so it can be revised or resubmitted.
        """
        self.action_draft()
        self.message_post(
            body=_("Recalled via Sarabun document: %s") % document.name,
        )

    def action_submit_to_sarabun(self):
        """Submit approval request to Sarabun for approval routing."""
        self.ensure_one()
        result = self.action_create_sarabun_document()
        document = self.env["sarabun.document"].browse(result.get("res_id"))
        self.message_post(
            body=_("Submitted to Sarabun for approval: %s") % document.name,
        )
        return {
            "type": "ir.actions.act_window",
            "res_model": "sarabun.document",
            "res_id": document.id,
            "view_mode": "form",
            "target": "current",
        }

    def _get_sarabun_report_action(self):
        """Delegate Sarabun report to Approval Request report."""
        return self.env.ref(
            "agx_approval.action_report_approval_request"
        )
