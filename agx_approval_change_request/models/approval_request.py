from odoo import _, models
from odoo.exceptions import UserError


class ApprovalRequest(models.Model):
    """Approval requests take Change requests: ผู้ตรวจสอบคำขอ and
    ผู้ยืนยันงบประมาณ detail what to fix as requests, and may close one on its
    author's behalf."""

    _name = "approval.request"
    _inherit = ["approval.request", "change.request.mixin"]

    def _change_request_can_close_on_behalf(self):
        self.ensure_one()
        user = self.env.user
        return user.has_group("agx_approval.group_approval_verify") or user.has_group(
            "agx_approval.group_approval_budget_commit"
        )

    def _outstanding_change_request_lines(self):
        """One line per outstanding Change request, for messages."""
        self.ensure_one()
        lines = []
        for request in self._get_outstanding_change_requests():
            line = "- #%s %s" % (request.id, request.text)
            if "file_name" in request._fields and request.file_name:
                line += _(" (ไฟล์ %(file)s หน้า %(page)s)") % {
                    "file": request.file_name,
                    "page": request.page,
                }
            lines.append(line)
        return lines

    def _send_back(self, reason):
        """ตีกลับ: the reason may be left out while Change requests are
        outstanding; they are listed in the chatter note (one per line)."""
        self.ensure_one()
        lines = self._outstanding_change_request_lines()
        reason = (reason or "").strip()
        if not reason and not lines:
            raise UserError(_("กรุณาระบุเหตุผลที่ตีกลับ หรือสร้างข้อแก้ไข"))
        if lines:
            reason = "\n".join(filter(None, [reason, _("ข้อแก้ไขที่ค้างอยู่:")] + lines))
        return super()._send_back(reason)
