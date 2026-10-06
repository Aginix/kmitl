# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import models


class DisbursementRequest(models.Model):
    _inherit = "disbursement.request"

    def _station_enter(self, code):
        super()._station_enter(code)
        if code == "payment_audit":
            # The payee set is final once the last bill is posted, which is what
            # lets the auditor see one row per payee the moment the request lands.
            self._ensure_payment_lines()

    def _station_check(self, code):
        super()._station_check(code)
        if code == "payment_audit":
            self._ensure_payment_lines()
            self._check_payment_classification()
