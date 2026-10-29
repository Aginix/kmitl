# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, models
from odoo.exceptions import AccessError, UserError
from odoo.tools import plaintext2html

# ตรวจสอบ waits until no Change request is outstanding; an administrator may
# switch the rule off.
OUTSTANDING_RULE = (
    "disbursement_change_request.excep_disbursement_outstanding_change_requests"
)


class DisbursementRequest(models.Model):
    """Disbursement requests take Change requests: the officer details what to
    fix as requests, and whoever may send the request back may close one on
    its author's behalf. ตรวจสอบ waits for them through an exception rule
    (``excep_disbursement_outstanding_change_requests``)."""

    _name = "disbursement.request"
    _inherit = ["disbursement.request", "change.request.mixin"]

    def _change_request_can_close_on_behalf(self):
        self.ensure_one()
        if self.state not in ("signed", "in_progress"):
            return False
        try:
            self._disbursement_check_send_back()
        except AccessError:
            return False
        return True

    def disbursement_request_check_outstanding_change_requests(self):
        # base.exception (by_method): return the requests that FAIL the rule.
        # Only in the circuit: the maker's resubmit after a return goes through
        # with the requests still answered, as the officer closes them.
        return self.filtered(
            lambda r: (
                r.state in ("signed", "in_progress")
                and r._get_outstanding_change_requests()
            )
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

    def action_validate(self):
        """ตรวจสอบ is refused while a Change request is outstanding."""
        rule = self.env.ref(OUTSTANDING_RULE, raise_if_not_found=False)
        failing = self.disbursement_request_check_outstanding_change_requests()
        if failing and rule and rule.sudo().active:
            raise UserError(
                "\n".join(
                    [rule.sudo().name] + failing[0]._outstanding_change_request_lines()
                )
            )
        return super().action_validate()

    def _action_return_for_edit(self, reason):
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
        return super()._action_return_for_edit(reason)
