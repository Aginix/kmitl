from odoo import _, models
from odoo.exceptions import AccessError, UserError

from odoo.addons.agx_related_document.models.related_document_mixin import (
    RelatedDocumentOne2many,
)

CLOSED_STATES = ("done", "cancel")


class AdvancePayment(models.Model):
    """The loan cites related documents through ``agx_related_document``,
    keeping its own label and its own rules on who may change them
    (advance_payment ADR-0029)."""

    _inherit = ["advance.payment", "related.document.mixin"]
    _name = "advance.payment"

    related_document_ids = RelatedDocumentOne2many(string="เอกสารอ้างอิงเพิ่มเติม")

    def _is_related_document_staff(self):
        """Unit finance (the User tier) and the loan officer, who implies it."""
        return self.env.user.has_group("advance_payment.group_advance_payment_user")

    def _related_document_check_change(self, rows, operation):
        """The borrower adds a row at any time and removes only the rows they
        added, while the request is a draft. Unit finance and the loan
        officer change any row. Nobody but an administrator changes the rows
        of a closed or cancelled loan. Others (an endorser) only read."""
        self.ensure_one()
        user = self.env.user
        if self.state in CLOSED_STATES and not user.has_group("base.group_system"):
            raise UserError(
                _(
                    "สัญญา %(loan)s ปิดหรือยกเลิกแล้ว แก้ไขเอกสารอ้างอิงไม่ได้",
                    loan=self.name,
                )
            )
        if self._is_related_document_staff():
            return
        if operation == "create":
            borrowers = self.sudo().employee_id.user_id | self.user_id
            if user not in borrowers:
                raise AccessError(_("เพิ่มเอกสารอ้างอิงได้เฉพาะผู้ยืมและฝ่ายการเงิน"))
        elif self.state != "draft" or rows.filtered(lambda r: r.added_by_id != user):
            raise UserError(_("ลบหรือแก้ไขได้เฉพาะเอกสารที่คุณเพิ่มเอง และขณะที่คำขอยังเป็นแบบร่าง"))
