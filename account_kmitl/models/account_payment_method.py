# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models

# KMITL's payment methods, seeded in data/account_payment_method.xml.
# ``sequence`` fixes the order they appear in on a journal, and therefore which
# one a new payment defaults to (account.payment._compute_payment_method_line_id
# takes the first available line). ``journal_types`` limits a method to the
# journals it makes sense on and must stay in sync with the domains declared in
# _get_payment_method_information below.
KMITL_PAYMENT_METHODS = [
    {
        "stem": "transfer",
        "code": "kmitl_transfer",
        "sequence": 10,
        "journal_types": ("bank",),
    },
    {
        "stem": "cheque",
        "code": "kmitl_cheque",
        "sequence": 20,
        "journal_types": ("bank",),
    },
    {
        "stem": "cash",
        "code": "kmitl_cash",
        "sequence": 30,
        "journal_types": ("bank", "cash"),
    },
]


def kmitl_method_xmlid(stem, payment_type):
    return "account_kmitl.payment_method_%s_%s" % (
        stem,
        "out" if payment_type == "outbound" else "in",
    )


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
        for method in KMITL_PAYMENT_METHODS:
            res[method["code"]] = {
                "mode": "multi",
                "domain": [("type", "in", list(method["journal_types"]))],
            }
        # Retire Odoo's stock Manual method: dropping it here takes it out of
        # account.journal.available_payment_method_ids, so it can no longer be
        # picked when adding a payment method line. Method lines that already
        # use it keep working (core looks this mapping up with .get).
        res.pop("manual", None)
        return res
