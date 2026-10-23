from odoo import _, models
from odoo.exceptions import UserError


class BudgetTransfer(models.Model):
    """Budget transfers take Change requests: the Buddy details what to fix
    as requests, ยืนยันตรวจสอบ is refused while any is outstanding, and a
    covering Buddy may close one on its author's behalf."""

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

    def action_verify(self):
        for transfer in self:
            lines = transfer._outstanding_change_request_lines()
            if lines:
                raise UserError(
                    _(
                        "ยังมีข้อขอแก้ไขที่ค้างอยู่ใน %(name)s "
                        "ต้องปิดให้ครบก่อนยืนยันตรวจสอบ:\n%(lines)s"
                    )
                    % {"name": transfer.name, "lines": "\n".join(lines)}
                )
        return super().action_verify()

    def _action_verify_return(self, reason):
        """ส่งกลับแก้ไข: the reason may be left out while Change requests are
        outstanding; they are listed in the note and the correction To-Do."""
        self.ensure_one()
        lines = self._outstanding_change_request_lines()
        reason = (reason or "").strip()
        if not reason and not lines:
            raise UserError(_("กรุณาระบุเหตุผลที่ส่งกลับแก้ไข หรือสร้างข้อขอแก้ไข"))
        if lines:
            reason = "\n".join(filter(None, [reason, _("ข้อขอแก้ไขที่ค้างอยู่:")] + lines))
        return super()._action_verify_return(reason)
