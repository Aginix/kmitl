# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import models


class DisbursementRequest(models.Model):
    _inherit = "disbursement.request"

    def _ensure_payment_lines(self):
        """Pick the payment subject by rule for a request that has none yet.

        Done after the rows exist, so setting the subject re-derives every
        payee's paying account through ``write`` exactly as a hand pick would.
        A subject already chosen is never overwritten, nor is one picked once a
        voucher exists. Sudo for the same reason as the rows: it is a system
        derivation run by whoever posted the last bill.
        """
        res = super()._ensure_payment_lines()
        Rule = self.env["disbursement.payment.subject.rule"].sudo()
        for record in self.sudo():
            if record.payment_subject_id or any(
                payment.state != "cancel" for payment in record.payment_ids
            ):
                continue
            rule = Rule._find_for_request(record)
            if rule:
                record.payment_subject_id = rule.payment_subject_id
        return res
