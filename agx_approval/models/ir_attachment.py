from odoo import fields, models


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    is_disbursement_evidence = fields.Boolean(
        string="Disbursement Evidence",
        default=False,
        help="แยกไฟล์ที่แนบในขั้นเบิกจ่าย (disbursement_attachment_ids) ออกจาก "
        "attachment_ids ของขั้นแผน — ทั้งคู่ถูกอัปโหลดด้วย res_model/res_id "
        "เดียวกัน จึงต้องมีธงนี้เป็นตัวแยก",
    )
