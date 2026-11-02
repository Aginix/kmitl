from odoo import _, models
from odoo.exceptions import UserError
from odoo.tools import plaintext2html

# Verify waits until no Change request is outstanding; an administrator may
# switch the rule off.
OUTSTANDING_RULE = (
    "advance_payment_change_request.excep_advance_payment_outstanding_change_requests"
)
# ส่งกลับแก้ไข with outstanding Change requests: one more marker (see
# advance_payment_return_exception), cleared on the next state change.
SENT_BACK_RULE = (
    "advance_payment_change_request.excep_advance_payment_sent_back_change_requests"
)


class AdvancePayment(models.Model):
    """Loans take Change requests: whoever checks the request details what to
    fix as requests, and whoever may send it back at its step may close one on
    its author's behalf. Verify waits for them through an exception rule."""

    _name = "advance.payment"
    _inherit = ["advance.payment", "change.request.mixin"]

    def _change_request_can_close_on_behalf(self):
        self.ensure_one()
        user = self.env.user
        if self.state == "to_endorse":
            return self.endorser_id == user
        if self.state == "to_director":
            return self.director_id == user
        if self.state == "to_verify":
            return self.loan_verifier_id == user
        return False

    def advance_payment_check_outstanding_change_requests(self):
        # base.exception (by_method): return the loans that FAIL the rule.
        # Only on Verify: elsewhere (submit, endorse, the officer's own edits)
        # outstanding requests hold nothing up.
        if not self.env.context.get("advance_payment_verifying"):
            return self.browse()
        return self.filtered(lambda r: r._get_outstanding_change_requests())

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
        """Verify is refused while a Change request is outstanding."""
        rule = self.env.ref(OUTSTANDING_RULE, raise_if_not_found=False)
        if rule and rule.sudo().active:
            failing = self.with_context(
                advance_payment_verifying=True
            ).advance_payment_check_outstanding_change_requests()
            if failing:
                raise UserError(
                    "\n".join(
                        [rule.sudo().name]
                        + failing[0]._outstanding_change_request_lines()
                    )
                )
        return super().action_verify()

    def _on_sent_back(self):
        """List the outstanding Change requests in the chatter and flag the
        loan มีข้อแก้ไขที่ต้องแก้ next to ส่งกลับแก้ไข."""
        res = super()._on_sent_back()
        marker = self.env.ref(SENT_BACK_RULE)
        for rec in self:
            lines = rec._outstanding_change_request_lines()
            if not lines:
                continue
            rec.message_post(
                body=plaintext2html("\n".join([_("ข้อแก้ไขที่ค้างอยู่:")] + lines)),
                subtype_xmlid="mail.mt_note",
            )
            rec.exception_ids = [(4, marker.id)]
        return res

    def _sent_back_rules(self):
        rule = self.env.ref(SENT_BACK_RULE, raise_if_not_found=False)
        return super()._sent_back_rules() | (rule or self.env["exception.rule"])
