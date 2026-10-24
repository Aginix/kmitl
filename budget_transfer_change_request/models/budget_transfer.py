from odoo import _, models
from odoo.exceptions import UserError
from odoo.tools import plaintext2html


class BudgetTransfer(models.Model):
    """Budget transfers take Change requests: the Buddy details what to fix
    as requests, and a covering Buddy may close one on its author's behalf.
    ยืนยันตรวจสอบ waits for them through an exception rule
    (``budget_transfer_exception_change_request``)."""

    _name = "budget.transfer"
    _inherit = ["budget.transfer", "change.request.mixin"]

    def _change_request_can_close_on_behalf(self):
        self.ensure_one()
        return self._is_covering_buddy()

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

    def _action_verify_return(self, reason):
        """ส่งกลับแก้ไข: the reason may be left out while Change requests are
        outstanding; they are listed in the note and the correction To-Do."""
        self.ensure_one()
        lines = self._outstanding_change_request_lines()
        reason = (reason or "").strip()
        if not reason and not lines:
            raise UserError(_("กรุณาระบุเหตุผลที่ส่งกลับแก้ไข หรือสร้างข้อแก้ไข"))
        if lines:
            # As HTML: the chatter note and the To-Do keep one line per request.
            reason = plaintext2html(
                "\n".join(filter(None, [reason, _("ข้อแก้ไขที่ค้างอยู่:")] + lines))
            )
        return super()._action_verify_return(reason)
