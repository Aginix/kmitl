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

    # The standing assignee for loan_verifier_id, which is required (ADR-0013).
    # Without it a multi-officer institute has no working default and every
    # create — including the bridges' programmatic ones — must name an officer
    # (ADR-0015). Domain mirrors the field's own on advance.payment.
    advance_payment_default_loan_verifier_id = fields.Many2one(
        comodel_name="res.users",
        string="เจ้าหน้าที่งานเงินยืมเริ่มต้น",
        config_parameter="advance_payment.default_loan_verifier_id",
        domain=lambda self: [
            (
                "groups_id",
                "in",
                self.env.ref(
                    "advance_payment.group_advance_payment_loan_officer"
                ).ids,
            )
        ],
        help="ผู้ที่จะถูกตั้งเป็นเจ้าหน้าที่งานเงินยืมของสัญญาใหม่ทุกฉบับ "
        "หากไม่ระบุ ระบบจะเลือกให้เองเมื่อมีเจ้าหน้าที่เพียงคนเดียว",
    )

    # The standing approver for approver_id. Unlike the loan officer there is
    # no sole-member to infer (root/admin are standing members of the approver
    # group), so this setting is the only real source; advance.payment falls
    # back to base.user_admin (ADR-0016). Domain mirrors the field's own,
    # which is scoped to the dedicated approver group, not manager (ADR-0017).
    advance_payment_default_approver_id = fields.Many2one(
        comodel_name="res.users",
        string="ผู้มีสิทธิ์อนุมัติเงินยืม",
        config_parameter="advance_payment.default_approver_id",
        domain=lambda self: [
            (
                "groups_id",
                "in",
                self.env.ref(
                    "advance_payment.group_advance_payment_loan_approver"
                ).ids,
            )
        ],
        help="ผู้ที่จะถูกตั้งเป็นผู้อนุมัติของสัญญาใหม่ทุกฉบับ และได้รับงานให้อนุมัติ "
        "เมื่อเจ้าหน้าที่ตรวจสอบคำขอเรียบร้อยแล้ว หากไม่ระบุ ระบบจะใช้ผู้ดูแลระบบ",
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
