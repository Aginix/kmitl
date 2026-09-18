from odoo import fields, models


class ApprovalCategory(models.Model):
    _inherit = "approval.category"

    guideline_html = fields.Html(
        string="คำอธิบายแบบฟอร์ม",
        help="คำอธิบาย ระเบียบ และเอกสารที่ต้องใช้ประกอบการยื่นคำขอ "
             "แสดงให้ผู้ใช้อ่านบนหน้าแบบฟอร์ม",
        sanitize=True,
    )
