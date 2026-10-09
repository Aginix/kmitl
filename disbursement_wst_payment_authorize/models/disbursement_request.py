# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, models
from odoo.exceptions import UserError, ValidationError


class DisbursementRequest(models.Model):
    _inherit = "disbursement.request"

    def _station_complete(self, code):
        super()._station_complete(code)
        if code == "payment_authorize":
            # The authorisation is what makes the money payable, so it is also what
            # issues the ใบสำคัญจ่าย (ADR-0006).
            self._try_create_payments()

    def _try_create_payments(self):
        """Raise the vouchers without letting a failure undo the authorisation.

        What can go wrong here is a banking coordinate — a payee with no account,
        a หัวจ่าย naming no bank — and none of it is the authorizer's to fix or to
        be stopped by. So the request is authorized either way: the reason goes in
        the chatter, the finance office's Todo stays where it is, and Create
        Payment is the way back in once the coordinate is corrected.

        The savepoint is what keeps a failed batch from taking the step with it;
        the message is posted outside it, or it would be rolled back too.

        Runs sudo because raising the vouchers is a system derivation: the
        authorizer holds no accounting rights, exactly as the accounting user who
        posts the last bill holds none on the payment lines ``_ensure_payment_lines``
        makes for them (ADR-0003). The finance office's own press keeps its own
        identity — a voucher they create is created by them.
        """
        self.ensure_one()
        try:
            with self.env.cr.savepoint():
                self.sudo()._create_payments()
        except (UserError, ValidationError) as error:
            self.env.invalidate_all()
            self.message_post(
                body=_(
                    "The payment vouchers could not be raised: %s Correct it, "
                    "then use Create Payment.",
                    error.args and error.args[0] or _("error"),
                ),
                subtype_xmlid="mail.mt_note",
            )
        return True
