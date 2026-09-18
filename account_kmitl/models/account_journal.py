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

    @api.depends("type")
    def _compute_payment_sequence(self):
        """Number a payment PV/… rather than PPV/….

        Core gives bank and cash journals a *dedicated payment sequence* so that
        payments do not share a running number with the invoices in the same
        journal: ``account.move._get_starting_sequence`` prefixes a "P" onto the
        journal code for payment moves whenever this is set.

        A KMITL journal code *is* the voucher type (ใบสำคัญ) and its sequence *is*
        the voucher number, so a voucher journal keeps one running number. There is
        nothing to keep the payments apart from anyway — a voucher journal carries
        payments and nothing else.

        Decided here rather than only in the install hook so that a journal an
        administrator adds later (a new หัวจ่าย held at another bank) is numbered
        the same way as the ones the hook creates. The hook still writes the flag on
        the journals that already exist when this module is installed, which no
        compute would reach.

        The dependency is restated because overriding a compute replaces the base
        decorator rather than adding to it.
        """
        self.payment_sequence = False
