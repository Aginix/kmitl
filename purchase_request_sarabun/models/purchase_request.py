# -*- coding: utf-8 -*-
from odoo import _, models


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

    def _get_sarabun_subject(self):
        return self.title

    def _get_sarabun_sender_department(self):
        return self.department_id or super()._get_sarabun_sender_department()

    def _on_sarabun_completed(self, document):
        self._transition_after_sarabun_approve()
        self.message_post(
            body=_("Approved via Sarabun document: %s") % document.name,
        )
        return super()._on_sarabun_completed(document)

    def _on_sarabun_rejected(self, document, step):
        self.button_rejected()
        return super()._on_sarabun_rejected(document, step)

    def _on_sarabun_returned(self, document, step):
        self.button_draft()
        return super()._on_sarabun_returned(document, step)

    def _on_sarabun_cancelled(self, document):
        self.button_draft()
        return super()._on_sarabun_cancelled(document)

    def _get_sarabun_report_action(self):
        """Delegate Sarabun report to Purchase Request report."""
        return self.env.ref("purchase_request.action_report_purchase_requests")
