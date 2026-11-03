from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    pa_auto_creator_id = fields.Many2one(
        comodel_name="res.users",
        string="ผู้สร้าง พจ.1 อัตโนมัติ",
        help="ชื่อที่แสดงเป็นผู้สร้าง พจ.1 ที่ระบบสร้างให้เมื่อหนังสือ พ.1 เสร็จสิ้น "
        "ว่างไว้ = OdooBot",
    )
