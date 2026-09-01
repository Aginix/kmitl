# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import api, models


class WithholdingTaxCert(models.Model):
    _inherit = "withholding.tax.cert"

    @api.depends(
        "payment_id.payment_export_id.effective_date",
        "payment_id.cheque_id.cheque_date",
    )
    def _compute_wht_cert_data(self):
        """Date the certificate the day the money left, not the day the voucher
        was raised.

        The two used to be the same day: the finance office made a voucher when
        it was about to go to the bank. Since a disbursement's vouchers are raised
        by the authorisation instead (``disbursement_finance_kmitl`` ADR-0006),
        the voucher carries the date it was authorised — which is its accounting
        period and what numbers it, and neither of those may move afterwards.

        The withholding, though, is dated by law from the day the payee was paid:
        ภ.ง.ด.3/53 is filed by the 7th of the month **following the month the
        income was paid**. Which record holds that day depends on how the money
        went:

        - a transfer: the e-payment file's **effective date**, the day the bank
          was told to move it;
        - a cheque: the **date written on the cheque**, because that is the day
          the payee may present it and therefore the day the Revenue Department
          treats the income as paid. Deliberately not the day the cheque was
          handed over, which has no tax effect — a cheque dated the 25th and
          collected on the 30th is September's withholding either way.

        Cash falls through to the base behaviour, the voucher's own date, which is
        the day it was paid across the counter.

        The base ``@api.depends`` is not repeated: overriding a compute keeps the
        method name, and Odoo unions the dependencies declared for it across the
        inheritance chain.
        """
        super()._compute_wht_cert_data()
        for rec in self:
            paid_on = (
                rec.payment_id.payment_export_id.effective_date
                or rec.payment_id.cheque_id.cheque_date
            )
            if paid_on:
                rec.date = paid_on
