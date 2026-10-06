# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    def _post(self, soft=True):
        """The accounting office posting a payment is the request being cleared.

        A voucher on a disbursement request may only post once the request has
        reached this station — the finance office has paid it in full. And once
        every voucher of the request is posted the station is done: the posting
        is the authority, so the step is completed without the group check.
        """
        dr_payments = self.env["account.payment"].search(
            [
                ("move_id", "in", self.ids),
                ("disbursement_request_id", "!=", False),
            ]
        )
        for payment in dr_payments:
            request = payment.disbursement_request_id
            if request.state == "in_progress" and request.station_code != "clear":
                raise UserError(
                    _(
                        "Payment %(payment)s cannot be posted: the disbursement "
                        "request %(dr)s is not confirmed paid by finance yet.",
                        payment=payment.name or payment.move_id.name,
                        dr=request.name,
                    )
                )
        res = super()._post(soft=soft)
        for request in dr_payments.disbursement_request_id:
            if request.station_code == "clear" and request._all_payments_posted():
                request.current_step_id.sudo()._do_complete()
        return res
