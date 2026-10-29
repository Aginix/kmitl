from odoo import api, fields, models


class ApprovalRequestSendBackConfirm(models.TransientModel):
    _inherit = "approval.request.send.back.confirm"

    reason = fields.Text(required=False)
    outstanding_requests = fields.Text(
        string="ข้อแก้ไขที่ค้างอยู่",
        compute="_compute_outstanding_requests",
    )

    @api.depends("request_id")
    def _compute_outstanding_requests(self):
        for wizard in self:
            wizard.outstanding_requests = (
                "\n".join(wizard.request_id._outstanding_change_request_lines())
                if wizard.request_id
                else False
            )

    def action_confirm(self):
        """No reason needed while Change requests are outstanding: ``_send_back``
        lists them in the note instead (the base insists on a reason)."""
        self.ensure_one()
        if (self.reason or "").strip() or not self.outstanding_requests:
            return super().action_confirm()
        self.request_id._send_back(self.reason)
        return {
            "type": "ir.actions.act_window",
            "res_model": "approval.request",
            "view_mode": "form",
            "res_id": self.request_id.id,
            "target": "current",
        }
