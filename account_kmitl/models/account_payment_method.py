# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class AccountPaymentMethod(models.Model):
    _inherit = "account.payment.method"

    @api.model
    def _get_payment_method_information(self):
        """Register the KMITL payment methods (เงินโอน / เช็ค / เงินสด).

        Odoo only accepts payment methods whose code is declared here; 'multi'
        lets the method be offered on any journal matching the domain. The
        method records themselves are seeded in
        ``data/account_payment_method.xml``.
        """
        res = super()._get_payment_method_information()
        res["kmitl_transfer"] = {
            "mode": "multi",
            "domain": [("type", "=", "bank")],
        }
        res["kmitl_cheque"] = {
            "mode": "multi",
            "domain": [("type", "=", "bank")],
        }
        res["kmitl_cash"] = {
            "mode": "multi",
            "domain": [("type", "in", ("bank", "cash"))],
        }
        return res
