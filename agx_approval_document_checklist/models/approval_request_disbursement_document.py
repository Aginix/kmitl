from odoo import api, fields, models


class ApprovalRequestDisbursementDocument(models.Model):
    """หนึ่งแถวของรายการเอกสารแนบที่ใช้ในการเบิกจ่ายบนคำขอ — snapshot ของ
    approval.category.disbursement.document ที่ถ่ายไว้ตอนเลือกประเภทคำขอ (ดู
    approval.request._sync_disbursement_documents). โครงสร้างถูกกำหนดโดยประเภทคำขอ:
    ผู้ขอทำได้เพียงแนบไฟล์ในขั้นบันทึกค่าใช้จ่ายจริง จะเพิ่ม/ลบ/แก้ชื่อ/แก้ธง
    'จำเป็น' ไม่ได้."""

    _name = "approval.request.disbursement.document"
    _description = "Approval Request Disbursement Document"
    _order = "sequence, id"

    request_id = fields.Many2one(
        string="Request",
        comodel_name="approval.request",
        required=True,
        ondelete="cascade",
        index=True,
    )

    name = fields.Char(
        string="เอกสาร",
        required=True,
    )

    required = fields.Boolean(
        string="จำเป็น",
    )

    sequence = fields.Integer(
        string="Sequence",
    )

    attachment_ids = fields.Many2many(
        comodel_name="ir.attachment",
        relation="approval_request_disb_doc_attachment_rel",
        column1="document_id",
        column2="attachment_id",
        string="ไฟล์แนบ",
    )

    attachment_count = fields.Integer(
        string="จำนวนไฟล์",
        compute="_compute_attachment_count",
    )

    is_fulfilled = fields.Boolean(
        string="แนบแล้ว",
        compute="_compute_attachment_count",
    )

    @api.depends("attachment_ids")
    def _compute_attachment_count(self):
        for rec in self:
            rec.attachment_count = len(rec.attachment_ids)
            rec.is_fulfilled = bool(rec.attachment_ids)

    # -- attachment ownership ----------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._adopt_orphan_attachments()
        return records

    def write(self, vals):
        result = super().write(vals)
        if "attachment_ids" in vals:
            self._adopt_orphan_attachments()
        return result

    def _adopt_orphan_attachments(self):
        """ผูก res_model/res_id ของไฟล์ที่เพิ่งอัปโหลดกลับมาที่แถวนี้.

        widget ``many2many_binary`` อัปโหลดด้วย ``res_id = <id ของ record ที่เปิดอยู่>``
        ซึ่งเป็น 0 เมื่อแถวยังไม่เคยถูกบันทึก — และนั่นคือเส้นทางปกติ (เลือกประเภทคำขอ
        → onchange สร้างแถว → แนบไฟล์ → ค่อยกด Save). ``ir.attachment.check()`` ปฏิเสธ
        การอ่าน attachment ที่ ``res_id`` ว่างให้ทุกคนที่ไม่ใช่ผู้อัปโหลดและไม่ได้อยู่ใน
        ``base.group_system`` ผู้ตรวจ/การเงินจึงเปิดหรือดาวน์โหลดเอกสารไม่ได้.

        ฟิลด์ ``attachment_ids`` ของ approval.request เป็น One2many บน ``res_id`` จึงได้
        การ stamp นี้ฟรีจาก ORM แต่ Many2many ไม่ได้ — ต้อง stamp เอง. รับเฉพาะไฟล์ที่
        ยังไม่มีเจ้าของ (``res_id`` ว่าง) เพื่อไม่ไปแย่ง attachment ของเอกสารอื่น."""
        for rec in self:
            orphans = rec.attachment_ids.sudo().filtered(lambda a: not a.res_id)
            if orphans:
                orphans.write({"res_model": rec._name, "res_id": rec.id})
