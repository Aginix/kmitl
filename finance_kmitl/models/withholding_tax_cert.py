# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import api, models


class WithholdingTaxCert(models.Model):
    _inherit = "withholding.tax.cert"

    @api.depends("payment_id.payment_export_id.effective_date")
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
        income was paid**. The only record of that day is the e-payment file's
        effective date, which is what the bank acted on. So the certificate reads
        it from there, and falls back to the base behaviour (the voucher's own
        date) for the vouchers that never travel in a file — cheques and cash,
        handed over on the day the voucher says.

        The base ``@api.depends`` is not repeated: overriding a compute keeps the
        method name, and Odoo unions the dependencies declared for it across the
        inheritance chain.
        """
        super()._compute_wht_cert_data()
        for rec in self:
            effective_date = rec.payment_id.payment_export_id.effective_date
            if effective_date:
                rec.date = effective_date
