# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import models


class DisbursementRequest(models.Model):
    _name = "disbursement.request"
    _inherit = ["disbursement.request", "sarabun.document.mixin"]

    def _get_sarabun_subject(self):
        source_name = (self.source_analytic_id.complete_name or "").replace(" / ", "")
        fy_name = self.account_fiscal_year_id.name or ""
        return f"ขออนุมัติเบิกเงิน{source_name} ประจำปีงบประมาณ พ.ศ.{fy_name}"

    def _prepare_sarabun_document_vals(self):
        vals = super()._prepare_sarabun_document_vals()
        vals["addressee"] = "อธิการบดี"
        return vals

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
        o = self.with_context(lang="th_TH")
        dept_name = (o.department_analytic_id.complete_name or "").replace(" / ", "")
        return (
            f"<p><span class='oe-tabs'>​ด้วย{dept_name} "
            "สถาบันเทคโนโลยีพระจอมเกล้าเจ้าคุณทหารลาดกระบัง "
            "มีความประสงค์ขอเบิกเงิน  ตามรายละเอียดดังนี้</span></p>"
        )
