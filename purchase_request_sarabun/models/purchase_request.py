# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class PurchaseRequest(models.Model):
    _name = 'purchase.request'
    _inherit = ["purchase.request", "sarabun.document.mixin", "portal.mixin", 'thai.date.mixin']

    # To disable tier validation
    # todo: refactor move out to individual module
    _state_from = [""]
    _state_to = [""]

    def _compute_access_url(self):
        """Compute the access URL for portal access."""
        super()._compute_access_url()
        for request in self:
            request.access_url = f"/my/purchase_request/{request.id}"

    def _get_report_base_filename(self):
        self.ensure_one()
        return 'Purchase Request-%s' % (self.name)

    def open_preview(self):
        if self.id:
            return {
                'type': 'ir.actions.act_url',
                'url': self.access_url,
                'target': 'new',
            }

    def _prepare_sarabun_document_vals(self):
        """Prepare values for creating a sarabun document."""
        self.ensure_one()
        vals = super()._prepare_sarabun_document_vals()
        vals["subject"] = self.title
        if self.department_id:
            vals["sender_department_id"] = self.department_id.id
        return vals

    def _on_sarabun_completed(self, document):
        """Called when sarabun document routing is completed."""
        _logger.info(
            "Sarabun completed callback for PR %s (id=%s) from document %s",
            self.name, self.id, document.name
        )
        self.button_approved()
        self.message_post(
            body=_("Approved via Sarabun document: %s") % document.name,
        )

    def _on_sarabun_rejected(self, document, step):
        """Called when the sarabun document is rejected (ปฏิเสธ, terminal).

        ``step`` is the rejecting routing step; the เกษียน reason lives on its
        outcome fields. Raises propagate to roll back the actor's disposition.
        """
        self.button_rejected()
        reason = step.note if step and step.note else _("No reason provided")
        self.message_post(
            body=_("Rejected via Sarabun. Reason: %s") % reason,
        )

    def _on_sarabun_returned(self, document, step):
        """Called when the sarabun document is returned for revision (ตีกลับ).

        Returned is revisable, so re-open the PR for editing/resubmission.
        """
        self.button_draft()
        reason = step.note if step and step.note else _("No reason provided")
        self.message_post(
            body=_("Returned via Sarabun for revision. Reason: %s") % reason,
        )

    def _on_sarabun_cancelled(self, document):
        """Called when the sarabun document is recalled/cancelled (เรียกคืน)."""
        self.button_draft()
        self.message_post(
            body=_("Recalled via Sarabun document: %s") % document.name,
        )

    def action_submit_to_sarabun(self):
        """Submit PR to Sarabun for approval routing."""
        self.ensure_one()
        result = self.action_create_sarabun_document()
        document = self.env["sarabun.document"].browse(result.get("res_id"))
        self.message_post(
            body=_("Submitted to Sarabun for approval: %s") % document.name,
        )
        # return document.action_select_route()
        return {
            "type": "ir.actions.act_window",
            "res_model": 'sarabun.document',
            "res_id": document.id,
            "view_mode": "form",
            "target": "current",
        }

    def _get_sarabun_report_action(self):
        """Delegate Sarabun report to Purchase Request report."""
        return self.env.ref("purchase_request.action_report_purchase_requests")
