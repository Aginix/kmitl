from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ApprovalRequest(models.Model):
    _inherit = "approval.request"

    disbursement_document_ids = fields.One2many(
        comodel_name="approval.request.disbursement.document",
        inverse_name="request_id",
        string="เอกสารแนบที่ใช้ในการเบิกจ่าย",
        copy=False,
    )

    # agx_approval_disbursement's bucket is now the *untyped* half of the pair:
    # once the category declares its documents, anything still landing here is
    # by definition something no requirement covers.
    disbursement_attachment_ids = fields.Many2many(
        string="เอกสารแนบอื่น ๆ",
    )

    # -- checklist materialisation -----------------------------------------
    def _sync_disbursement_documents(self):
        """สร้างรายการเอกสารแนบใหม่จาก category_id.disbursement_document_ids โดยถ่าย
        name/required/sequence เป็น snapshot แบบเดียวกับ line_ids/participant_ids.

        เรียกเฉพาะตอนที่ประเภทคำขอเปลี่ยนจริง (onchange ด้านล่าง), ตอนสร้างเรคคอร์ด และ
        ตอนเข้าสถานะ approved ถ้ายังไม่มีแถวเลย — การเขียนฟิลด์อื่นจึงไม่มีวันล้างไฟล์
        ที่แนบไว้แล้ว."""
        for rec in self:
            rows = [(5, 0, 0)]
            for req in rec.category_id.disbursement_document_ids:
                rows.append(
                    (0, 0, {
                        "name": req.name,
                        "required": req.required,
                        "sequence": req.sequence,
                    })
                )
            rec.disbursement_document_ids = rows

    @api.onchange("category_id")
    def _onchange_category_id(self):
        result = super()._onchange_category_id()
        self._sync_disbursement_documents()
        return result

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            # คำขอที่ถูกสร้างจากโค้ดไม่เคยผ่าน onchange ของฟอร์ม ถ้าไม่เติมตรงนี้
            # รายการเอกสารแนบจะว่าง แล้วด่านตรวจก่อนส่งการเงินจะผ่านไปเฉย ๆ
            if rec.category_id and not rec.disbursement_document_ids:
                rec._sync_disbursement_documents()
        return records

    def write(self, vals):
        result = super().write(vals)
        if vals.get("state") == "approved":
            # เติมรายการให้คำขอที่มีอยู่ก่อนติดตั้งโมดูลนี้ (จึงไม่เคยผ่าน onchange/create
            # ที่มีการ sync) ตอนเข้าสู่ขั้นบันทึกค่าใช้จ่ายจริงซึ่งเป็นที่ที่ต้องใช้จริง
            for rec in self:
                if rec.category_id and not rec.disbursement_document_ids:
                    rec._sync_disbursement_documents()
        return result

    # -- gate: ส่งให้การเงินตรวจสอบ -----------------------------------------
    def _check_disbursement_documents(self):
        """บล็อก approved → to_disburse เมื่อเอกสารแนบที่ใช้ในการเบิกจ่ายซึ่งติ๊ก
        'จำเป็น' ยังไม่มีไฟล์แนบ (นับว่าครบเมื่อมีไฟล์อย่างน้อย 1 ไฟล์ต่อแถว).

        ตรวจตรง ๆ แทนที่จะเพิ่ม exception.rule แล้วเรียก ``detect_exceptions()``:
        ที่ด่านนี้ ``detect_exceptions()`` จะประเมินกฎ *ทั้งหมด* ของ approval.request
        ซ้ำอีกครั้ง รวมถึง ``excep_submit_date_outside_fy`` ที่เทียบ "วันนี้" กับปีงบ
        ประมาณ — คำขอที่อนุมัติปลายปีงบแล้วมาเบิกหลัง 1 ต.ค. (ซึ่งเป็นเรื่องปกติ) จะ
        ถูกบล็อกด้วยเหตุผลที่ไม่เกี่ยวกับเอกสารแนบเลย."""
        for rec in self.filtered(lambda r: r.state == "approved"):
            missing = rec.disbursement_document_ids.filtered(
                lambda d: d.required and not d.attachment_ids
            )
            if missing:
                raise UserError(
                    _(
                        "กรุณาแนบเอกสารแนบที่ใช้ในการเบิกจ่ายให้ครบก่อนส่งให้การเงิน:\n%s"
                    )
                    % "\n".join("- %s" % doc.name for doc in missing)
                )

    def action_open_submit_finance_wizard(self):
        self._check_disbursement_documents()
        return super().action_open_submit_finance_wizard()

    def action_submit_to_finance(self):
        self._check_disbursement_documents()
        return super().action_submit_to_finance()
