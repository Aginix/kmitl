# -*- coding: utf-8 -*-
from odoo import models


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

    def _on_sarabun_completed(self, document):
        self.state = "approved"
        return super()._on_sarabun_completed(document)

    def _on_sarabun_rejected(self, document, step):
        # ปฏิเสธ is terminal: action_cancel lands the request in ``rejected`` and
        # releases the budget commitment.
        self.action_cancel()
        return super()._on_sarabun_rejected(document, step)

    def _on_sarabun_returned(self, document, step):
        # ตีกลับ / ดึงกลับ are revisable: re-open to draft for amend & resubmit.
        self.action_draft()
        return super()._on_sarabun_returned(document, step)

    def _on_sarabun_cancelled(self, document):
        # ยกเลิกการส่ง (terminal): re-open to draft so it can be revised/resubmitted.
        self.action_draft()
        return super()._on_sarabun_cancelled(document)

    def _get_sarabun_report_action(self):
        """Delegate Sarabun report to Approval Request report."""
        return self.env.ref("agx_approval.action_report_approval_request")
