# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, models
from odoo.exceptions import UserError


class DisbursementRequest(models.Model):
    _name = "disbursement.request"
    _inherit = ["disbursement.request", "sarabun.document.mixin"]

    def _get_sarabun_subject(self):
        source_name = (self.source_analytic_id.complete_name or "").replace(" / ", "")
        department_name = (self.department_analytic_id.complete_name or "").replace(
            " / ", ""
        )
        fy_name = self.account_fiscal_year_id.name or ""
        return (
            f"ขออนุมัติเบิกเงิน{source_name} {department_name} ประจำปีงบประมาณ พ.ศ. {fy_name}"
        )

    def _prepare_sarabun_document_vals(self):
        vals = super()._prepare_sarabun_document_vals()
        vals["addressee"] = "อธิการบดี"
        return vals

    def _sarabun_submit_guard(self):
        return self.state == "submitted"

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

    # A requester may now reset or cancel before approval: not while its
    # หนังสือ is still in e-Saraban, which would leave it routing for nothing.
    # Every e-Saraban callback moves the หนังสือ off ``circulating`` before it
    # calls back, so this only stops the manual action.
    def _check_no_circulating_sarabun(self):
        documents = (
            self.env["sarabun.document"]
            .sudo()
            .search(
                [
                    ("origin_model", "=", self._name),
                    ("origin_res_id", "in", self.ids),
                    ("state", "=", "circulating"),
                ]
            )
        )
        if documents:
            # Not named: a หนังสือ has no number until its issuing sign.
            raise UserError(
                _(
                    "This request's memo is still circulating in e-Saraban: "
                    "pull it back or cancel sending it there first."
                )
            )

    def action_draft(self):
        self._check_no_circulating_sarabun()
        return super().action_draft()

    def action_cancel(self):
        self._check_no_circulating_sarabun()
        return super().action_cancel()

    def _on_sarabun_numbered(self, document):
        """เลขที่หนังสือ follows the number e-Saraban just issued."""
        self.memo_number = document.name
        return super()._on_sarabun_numbered(document)

    # -- Sarabun outcome → disbursement state (mirrors kmitl_project_sarabun) --
    def _on_sarabun_circulating(self, document):
        # ส่งใหม่หลังตีกลับ/ดึงกลับ: resync กลับเป็น ``submitted`` ให้สอดคล้องกับ
        # หนังสือที่กลับมาเดินใหม่ (เผื่อ user re-send จากหนังสือโดยไม่ได้กด Submit
        # เอง) เพื่อให้ ``_on_sarabun_completed → action_sign`` เจอ state ที่ถูกต้อง.
        if self.state == "draft":
            self.state = "submitted"
        return super()._on_sarabun_circulating(document)

    def _on_sarabun_completed(self, document):
        """Head approved in Sarabun → advance to signed."""
        if self.state == "submitted":
            self.action_sign()
        return super()._on_sarabun_completed(document)

    def _on_sarabun_returned(self, document, step):
        # ตีกลับ / ดึงกลับ: เปิดคำขอให้แก้ไข (กลับ ``draft``) — งบคงอยู่ (action_draft
        # ไม่คืน commitment) แก้แล้วเปิดหนังสือ (returned) กด ส่งใหม่ หนังสือจะพาคำขอ
        # กลับเข้า ``submitted`` ผ่าน ``_on_sarabun_circulating``.
        if self.state == "submitted":
            self.action_draft()
        return super()._on_sarabun_returned(document, step)

    def _on_sarabun_rejected(self, document, step):
        # ปฏิเสธ (terminal): ยกเลิกคำขอ — budget commitment จะถูกคืนผ่าน ``_on_cancel``
        # ของ disbursement_budget.
        if self.state != "cancel":
            self.action_cancel()
        return super()._on_sarabun_rejected(document, step)

    def _on_sarabun_cancelled(self, document):
        # ยกเลิกการส่ง: หนังสือฉบับนั้นถูกยกเลิก (เลขถูก void) แต่คำขอยังอยู่ที่
        # ``submitted`` พร้อมสร้างหนังสือใหม่ (ปุ่ม "Submit to Sarabun" กลับมาเพราะ
        # sarabun_has_live_document เป็น False) — ล้างเลขที่หนังสือที่ถูก void ออก
        # หนังสือฉบับใหม่จะ stamp เลขใหม่ให้เอง.
        if self.memo_number == document.name:
            self.memo_number = False
        return super()._on_sarabun_cancelled(document)

    def _get_sarabun_document_type(self):
        return (
            self.env.ref(
                "disbursement_sarabun.document_type_disbursement_request",
                raise_if_not_found=False,
            )
            or super()._get_sarabun_document_type()
        )

    def _get_sarabun_body_template(self):
        return "disbursement_sarabun.report_disbursement_request_body"

    def _get_sarabun_content(self):
        """The editable เนื้อหา, seeded once at submit: the opening paragraph,
        then the request's รายละเอียด. Edited on the หนังสือ from then on; the
        tables render live (``_get_sarabun_body_template``)."""
        self.ensure_one()
        o = self.with_context(lang="th_TH")
        source_name = (o.source_analytic_id.complete_name or "").replace(" / ", "")
        dept_name = (o.department_analytic_id.complete_name or "").replace(" / ", "")
        fy_name = self.account_fiscal_year_id.name or ""
        content = (
            f"<p style='text-indent: 2em;'>ด้วย{dept_name} "
            "สถาบันเทคโนโลยีพระจอมเกล้าเจ้าคุณทหารลาดกระบัง "
            f"มีความประสงค์ขอเบิกเงิน{source_name} ประจำปีงบประมาณ พ.ศ. {fy_name}</p>"
        )
        if self._has_description():
            # str(): ``note`` is Markup, whose __radd__ would escape ``content``.
            content += str(self.note)
        return content
