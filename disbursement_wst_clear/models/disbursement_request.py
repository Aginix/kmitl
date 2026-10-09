# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, models
from odoo.exceptions import UserError

TO_BOOK_ACTIVITY = "disbursement_wst_clear.mail_activity_dr_to_book"


class DisbursementRequest(models.Model):
    _inherit = "disbursement.request"

    def _all_payments_posted(self):
        """Every live voucher of the request is posted — and there is one."""
        self.ensure_one()
        active = self.payment_ids.filtered(lambda p: p.state != "cancel")
        return bool(active) and all(p.state == "posted" for p in active)

    def _station_check(self, code):
        super()._station_check(code)
        if code == "clear" and not self._all_payments_posted():
            raise UserError(
                _("Every payment of the request must be posted before it is cleared.")
            )

    def action_submit_payments(self):
        """The accounting maker submits every voucher of a paid request at once.

        Their step is per voucher — correct the booking, then submit — but a request
        whose vouchers need no correction is the same press repeated, and the request
        is the document they navigate by. A voucher that does need work is opened
        from the queue and submitted on its own entry instead.

        Submitting is what asks the approver: ``account.move.action_submit`` puts the
        Todo in their inbox, so the makers' own Todo on the request is cleared here.
        """
        for record in self:
            if record.station_code != "clear":
                raise UserError(
                    _("Only a request the finance office has paid can be booked.")
                )
            active = record.payment_ids.filtered(lambda p: p.state != "cancel")
            drafts = active.move_id.filtered(lambda move: move.state == "draft")
            if not drafts:
                raise UserError(
                    _("Every voucher of %s is already submitted.") % record.display_name
                )
            result = drafts.action_submit()
            if isinstance(result, dict):
                # base_exception wants to show a popup, and a queue has nobody to
                # show it to: report it as the reason this request could not be
                # booked rather than leaving the vouchers silently in draft.
                raise UserError(
                    _(
                        "%s has vouchers with blocking exceptions. Open the entry "
                        "and submit it there to see them."
                    )
                    % record.display_name
                )
            record.activity_feedback([TO_BOOK_ACTIVITY])
        return True

    def action_submit_payments_batch(self):
        return self._run_batch("action_submit_payments")
