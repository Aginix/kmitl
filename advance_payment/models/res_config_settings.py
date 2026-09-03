from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    advance_payment_allow_manual_reference = fields.Boolean(
        string="Allow Manual Reference",
        config_parameter="advance_payment.allow_manual_reference",
        help="เมื่อเปิด ผู้ใช้สามารถระบุเอกสารอ้างอิง (Reference) เองได้ตอนสร้างสัญญา "
        "หากปิด จะระบุได้เฉพาะจากระบบเท่านั้น (เช่น สร้างจากใบขอซื้อ)",
    )

    advance_payment_strict_own_only = fields.Boolean(
        string="สร้างสัญญาของตนเองเท่านั้น",
        config_parameter="advance_payment.strict_own_only",
        help="เมื่อเปิด ผู้ยืมบนสัญญาจะเป็นตัวผู้จัดทำเองเสมอ แก้ไม่ได้ทุกสิทธิ์ "
        "(ยกเว้นผู้ดูแลระบบ) หากปิด สิทธิ์ระดับ User ขึ้นไปจะดราฟต์แทนผู้ยืมคนอื่นได้",
    )

    # A rich-text Html field cannot use config_parameter= — res.config.settings
    # only allows boolean/integer/float/char/selection/many2one/datetime on that
    # path (_get_classified_fields raises otherwise). Bridge it to the
    # ir.config_parameter manually via get_values/set_values instead.
    advance_payment_terms_conditions = fields.Html(
        string="เงื่อนไขและข้อตกลงการยืมเงินทดรองจ่าย",
        help="ข้อความเงื่อนไขและข้อตกลงเริ่มต้น แสดงบนสัญญายืมเงินทุกฉบับ",
    )

    def get_values(self):
        res = super().get_values()
        res["advance_payment_terms_conditions"] = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("advance_payment.terms_conditions")
        )
        return res

    def set_values(self):
        super().set_values()
        self.env["ir.config_parameter"].sudo().set_param(
            "advance_payment.terms_conditions",
            self.advance_payment_terms_conditions or "",
        )
