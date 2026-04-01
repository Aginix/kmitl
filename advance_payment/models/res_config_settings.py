from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    advance_payment_strict_submit = fields.Boolean(
        string="Strict Submit Mode",
        config_parameter="advance_payment.strict_submit",
        help="เมื่อเปิดโหมดนี้ เฉพาะผู้ยืมหรือ Admin เท่านั้นที่สามารถส่งขออนุมัติได้ "
        "หากปิด ผู้ยืม, ผู้จัดการ หรือ Admin สามารถส่งขออนุมัติได้",
    )

    advance_payment_allow_manual_reference = fields.Boolean(
        string="Allow Manual Reference",
        config_parameter="advance_payment.allow_manual_reference",
        help="เมื่อเปิด ผู้ใช้สามารถระบุเอกสารอ้างอิง (Reference) เองได้ตอนสร้างสัญญา "
        "หากปิด จะระบุได้เฉพาะจากระบบเท่านั้น (เช่น สร้างจากใบขอซื้อ)",
    )
