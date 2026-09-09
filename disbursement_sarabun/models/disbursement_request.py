# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, models


class DisbursementRequest(models.Model):
    _name = "disbursement.request"
    _inherit = ["disbursement.request", "sarabun.document.mixin"]

    def _get_sarabun_subject(self):
        return _("Disbursement Request: %s") % self.name

    def _sarabun_submit_guard(self):
        return self.state == "submitted"

    def _on_sarabun_completed(self, document):
        """Head approved in Sarabun → advance to signed."""
        if self.state == "submitted":
            self.action_sign()
        return super()._on_sarabun_completed(document)

    # ตีกลับ / ปฏิเสธ / ยกเลิกการส่ง are audit-only for a disbursement (it stays
    # ``submitted`` and a resubmission spawns a new document) — the mixin's default
    # callbacks post the actor + reason note, so no override is needed.

    def _get_sarabun_document_type(self):
        return self.env.ref(
            "disbursement_sarabun.document_type_disbursement_request",
            raise_if_not_found=False,
        ) or super()._get_sarabun_document_type()

    def _get_sarabun_body_template(self):
        return "disbursement_sarabun.report_disbursement_request_body"

    def _get_sarabun_content(self):
        self.ensure_one()
        return self.env["ir.qweb"]._render(
            "disbursement_sarabun.report_disbursement_request_narrative",
            {"o": self.with_context(lang="th_TH")},
        )
