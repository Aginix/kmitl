from odoo import _, api, fields, models
from odoo.exceptions import UserError

VERIFY_GROUP = "agx_approval.group_approval_verify"


class ApprovalRequest(models.Model):
    _inherit = "approval.request"

    verifier_id = fields.Many2one(
        "res.users",
        string="ผู้ตรวจสอบที่ระบุ",
        default=lambda self: self._default_verifier_id(),
        domain=lambda self: [("groups_id", "in", self.env.ref(VERIFY_GROUP).ids)],
        tracking=True,
        index=True,
        help="ผู้ตรวจสอบคำขอที่ผู้ขอระบุให้ตรวจสอบคำขอนี้ — รับ Todo เมื่อคำขอเข้า "
        "สถานะรอตรวจสอบข้อมูล. ไม่ได้ล็อกสิทธิ์: ผู้ตรวจสอบคำขอคนอื่นยังยืนยัน"
        "ตรวจสอบหรือตีกลับได้",
    )

    @api.model
    def _verifier_default_domain(self):
        return [("user_id", "=", self.env.uid), ("verifier_id", "!=", False)]

    @api.model
    def _default_verifier_id(self):
        """The Designated Verifier of the user's most recent request, if they
        are still a Request Verifier."""
        verifier = self.search(
            self._verifier_default_domain(), order="id desc", limit=1
        ).verifier_id
        return verifier if verifier and verifier.has_group(VERIFY_GROUP) else False

    def action_to_verify(self):
        if self.filtered(lambda rec: not rec.verifier_id):
            raise UserError(_("กรุณาระบุผู้ตรวจสอบที่ระบุก่อนส่งตรวจสอบ"))
        return super().action_to_verify()
