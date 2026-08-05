from odoo import _, fields, models
from odoo.exceptions import UserError


class ApprovalRequestPullBackConfirm(models.TransientModel):
    """ดึงกลับ (pre-routing) confirmation — returns a not-yet-sent request to
    draft, releasing its budget reservation."""

    _name = "approval.request.pull.back.confirm"
    _description = "Approval Request Pull Back Confirmation"

    request_id = fields.Many2one(
        "approval.request",
        string="Request",
        required=True,
        ondelete="cascade",
    )

    reason = fields.Text(string="เหตุผล")

    def action_confirm(self):
        self.ensure_one()
        request = self.request_id
        if request.state not in ("to_verify", "to_send"):
            raise UserError(
                _("ดึงกลับได้เฉพาะสถานะ 'รอตรวจสอบ' หรือ 'รอส่งขออนุมัติ'")
            )
        request.action_draft()
        request.message_post(
            body=_("ดึงกลับคำขอกลับสู่ร่าง%s")
            % ((": %s" % self.reason) if self.reason else "")
        )
        return {
            "type": "ir.actions.act_window",
            "res_model": "approval.request",
            "view_mode": "form",
            "res_id": request.id,
            "target": "current",
        }
