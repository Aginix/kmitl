from odoo import fields, models


class ApprovalCategoryDisbursementDocument(models.Model):
    """เอกสารแนบที่ใช้ในการเบิกจ่ายหนึ่งรายการที่ประเภทคำขอกำหนดไว้ เช่น ใบเสร็จ,
    สำเนาบัตรประชาชน, ใบสำคัญรับเงิน. เป็นการตั้งค่าต่อประเภทคำขอ (ไม่ใช่ทะเบียน
    ประเภทเอกสารกลาง) และถูก materialise ลงคำขอแต่ละใบเป็นแถวของรายการเอกสารแนบ
    (approval.request.disbursement.document)."""

    _name = "approval.category.disbursement.document"
    _description = "Approval Category Disbursement Document Requirement"
    _order = "sequence, id"

    category_id = fields.Many2one(
        string="Category",
        comodel_name="approval.category",
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
        default=False,
        help="ถ้าติ๊ก ต้องแนบไฟล์อย่างน้อย 1 ไฟล์ จึงจะส่งคำขอให้การเงินตรวจสอบได้",
    )

    sequence = fields.Integer(
        string="Sequence",
    )
