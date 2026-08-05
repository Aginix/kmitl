from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    advance_payment_allow_manual_reference = fields.Boolean(
        string="Allow Manual Reference",
        config_parameter="advance_payment.allow_manual_reference",
        help="เมื่อเปิด ผู้ใช้สามารถระบุเอกสารอ้างอิง (Reference) เองได้ตอนสร้างสัญญา "
        "หากปิด จะระบุได้เฉพาะจากระบบเท่านั้น (เช่น สร้างจากใบขอซื้อ)",
    )
