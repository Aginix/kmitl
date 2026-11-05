# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import models


class DisbursementRequest(models.Model):
    _inherit = "disbursement.request"

    def _ensure_payment_lines(self):
        """Pick the payment subject by rule for every payment line that has
        none yet.

        Done after the rows exist, so setting the subject re-derives the
        payee's paying account through ``write`` exactly as a hand pick would.
        A subject already chosen is never overwritten, nor is one picked once
        the row's voucher exists. Sudo for the same reason as the rows: it is a
        system derivation run by whoever posted the last bill.
        """
        res = super()._ensure_payment_lines()
        Rule = self.env["disbursement.payment.subject.rule"].sudo()
        for line in self.sudo().payment_line_ids:
            if line.payment_subject_id or line.payment_id:
                continue
            rule = Rule._find_for_payment_line(line)
            if rule:
                line.payment_subject_id = rule.payment_subject_id
        return res
