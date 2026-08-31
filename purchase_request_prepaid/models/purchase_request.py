from odoo import _, api, models
from odoo.exceptions import ValidationError


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    @api.onchange("payment_type")
    def _onchange_payment_type_prepaid(self):
        if self.payment_type == "prepaid":
            if self.procurement_mode != "by_requester":
                self.procurement_mode = "by_requester"
            if self.partner_id and not self.partner_id.user_ids.employee_ids:
                self.partner_id = False

    @api.constrains("payment_type", "procurement_mode", "partner_id")
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
            if rec.partner_id and not rec.partner_id.user_ids.employee_ids:
                raise ValidationError(
                    _(
                        "กรณีวิธีการจ่ายเงินเป็นสำรองจ่าย "
                        "คู่ค้าต้องเป็นบุคลากรภายในที่มีข้อมูลพนักงาน (hr.employee) เท่านั้น"
                    )
                )
