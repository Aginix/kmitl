from odoo import _, fields, models
from odoo.exceptions import UserError


class ApprovalRequestSendBackConfirm(models.TransientModel):
    """ตีกลับ (to_commit → to_verify / to_verify → draft) — reason is mandatory
    and is posted in the same chatter message as the state change (via
    _track_set_log_message)."""

    _name = "approval.request.send.back.confirm"
    _description = "Confirm Send Back Approval Request"

    request_id = fields.Many2one(
        "approval.request",
        string="Request",
        required=True,
        ondelete="cascade",
    )
    reason = fields.Text(string="เหตุผลที่ตีกลับ", required=True)

    def action_confirm(self):
        self.ensure_one()
        if not (self.reason or "").strip():
            raise UserError(_("กรุณากรอกเหตุผลในการตีกลับ"))
        self.request_id._send_back(self.reason)
        return {
            "type": "ir.actions.act_window",
            "res_model": "approval.request",
            "view_mode": "form",
            "res_id": self.request_id.id,
            "target": "current",
        }
