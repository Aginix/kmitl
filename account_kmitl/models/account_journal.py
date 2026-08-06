# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models

from .account_payment_method import KMITL_PAYMENT_METHODS, kmitl_method_xmlid


class AccountJournal(models.Model):
    _inherit = "account.journal"

    def _kmitl_default_payment_methods(self, payment_type):
        """KMITL's methods (เงินโอน / เช็ค / เงินสด) applicable to this journal.

        Returned in configured order so the method lines core creates keep that
        order, and so a new payment defaults to เงินโอน on a bank journal.
        """
        journal_type = self.type if self else "bank"
        methods = self.env["account.payment.method"]
        for method in KMITL_PAYMENT_METHODS:
            if journal_type not in method["journal_types"]:
                continue
            record = self.env.ref(
                kmitl_method_xmlid(method["stem"], payment_type),
                raise_if_not_found=False,
            )
            if record:
                methods |= record
        return methods

    def _kmitl_cheque_method_line(self, payment_type):
        """The journal's เช็ค method line for the given direction, if any.

        Returns an empty recordset when called on no journal (a payment whose
        journal is left to Odoo to pick), so callers can simply skip.
        """
        if not self:
            return self.env["account.payment.method.line"]
        self.ensure_one()
        return self._get_available_payment_method_lines(payment_type).filtered(
            lambda line: line.payment_method_id.code == "kmitl_cheque"
        )[:1]

    @api.model
    def _default_inbound_payment_methods(self):
        """Offer KMITL's methods instead of Odoo's stock Manual one.

        Core seeds a journal's payment method lines from these defaults, both
        when the journal is created and whenever its type or currency changes
        (the stored computes clear and rebuild the lines). Overriding them is
        what keeps Manual out of every bank/cash journal — including the
        per-bank journals an administrator adds after install — rather than
        only the journals the install hook happens to touch. Falls back to the
        stock method while the KMITL data is not loaded yet (e.g. journals
        created by a dependency's chart before this module installs).
        """
        return (
            self._kmitl_default_payment_methods("inbound")
            or super()._default_inbound_payment_methods()
        )

    @api.model
    def _default_outbound_payment_methods(self):
        return (
            self._kmitl_default_payment_methods("outbound")
            or super()._default_outbound_payment_methods()
        )
