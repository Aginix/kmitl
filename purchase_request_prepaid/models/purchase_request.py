from odoo import _, api, models
from odoo.exceptions import ValidationError


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    def _compute_partner_id_domain(self):
        super()._compute_partner_id_domain()
        for rec in self:
            if rec.payment_type == "prepaid":
                rec.partner_id_domain = [("partner_type_id.is_internal", "=", True)]

    @api.depends("is_editable", "payment_type")
    def _compute_is_vat_editable(self):
        super()._compute_is_vat_editable()
        for rec in self:
            if rec.payment_type == "prepaid":
                rec.is_vat_editable = False

    @api.onchange("payment_type")
    def _onchange_payment_type_prepaid(self):
        if self.payment_type == "prepaid":
            if self.procurement_mode != "by_requester":
                self.procurement_mode = "by_requester"
            if self.vat_included != "exclusive":
                self.vat_included = "exclusive"
                self.tax_id = False
            if self.partner_id and not self.partner_id.partner_type_id.is_internal:
                self.partner_id = False

    @api.constrains(
        "payment_type", "procurement_mode", "partner_id", "vat_included"
    )
    def _check_prepaid_partner(self):
        for rec in self:
            if rec.payment_type != "prepaid":
                continue
            if rec.procurement_mode == "by_officer":
                raise ValidationError(
                    _(
                        "กรณีวิธีการจ่ายเงินเป็นสำรองจ่าย "
                        "ไม่สามารถเลือกโหมดจัดหาเป็น 'ให้พัสดุจัดหา' ได้"
                    )
                )
            if rec.vat_included != "exclusive":
                raise ValidationError(
                    _(
                        "กรณีวิธีการจ่ายเงินเป็นสำรองจ่าย "
                        "ต้องไม่มีภาษีมูลค่าเพิ่ม (VAT Exclusive) เท่านั้น"
                    )
                )
            if rec.partner_id and not rec.partner_id.partner_type_id.is_internal:
                raise ValidationError(
                    _(
                        "กรณีวิธีการจ่ายเงินเป็นสำรองจ่าย "
                        "คู่ค้าต้องเป็นบุคลากรภายใน "
                        "(partner type ที่ตั้งค่า is_internal) เท่านั้น"
                    )
                )
