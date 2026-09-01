# -*- coding: utf-8 -*-
from odoo import _, models
from odoo.exceptions import UserError


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

    def _on_sarabun_circulating(self, document):
        self.write({"state": "to_approve"})
        return super()._on_sarabun_circulating(document)

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
        self._action_do_return(post_message=False)
        return super()._on_sarabun_returned(document, step)

    def action_resend_to_sarabun(self):
        self.ensure_one()
        document = self.active_sarabun_document_id
        if not document:
            raise UserError(_("No active Sarabun document to resend."))
        return document.action_send()

    def _on_sarabun_cancelled(self, document):
        self.button_draft()
        return super()._on_sarabun_cancelled(document)

    # ADR-0015: render through Sarabun's own no-source layout (สารบรรณ owns the
    # header — เลขที่/หน่วยงาน/เรียน/วันที่/อ้างถึง — and the endorsement block).
    # We therefore DON'T override _get_sarabun_report_action (mixin default →
    # False), and instead contribute:
    #   - the editable บรรยาย via _get_sarabun_content (seeded once at submit), and
    #   - the live tables (items / budget / attachments / committees) via
    #     _get_sarabun_body_template.

    def _get_sarabun_body_template(self):
        """The live body — items table, budget details, enclosure list, committee
        appointments — rendered between the หนังสือ's เนื้อหา and its signatures
        (ADR-0015). Kept live so the official หนังสือ can never show numbers that
        diverge from the reserved commitment."""
        return "purchase_request_sarabun.report_purchase_request_body"

    def _get_sarabun_content(self):
        """The editable บรรยาย seeding เนื้อหา (policy 5A: seeded once at submit,
        then owned by the user). The authoritative tables render live via
        _get_sarabun_body_template — never seeded here."""
        self.ensure_one()
        return self.env["ir.qweb"]._render(
            "purchase_request_sarabun.report_purchase_request_narrative",
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
        ACL governs. Seeded once at submit; the drafter then manages enclosures on
        the หนังสือ itself."""
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
