# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

# The KMITL methods that move money through a bank and therefore need one.
BANKED_METHOD_CODES = ("kmitl_transfer", "kmitl_cheque")


class AccountPaymentMethodLine(models.Model):
    """หัวจ่าย — a payment method line that knows where the money comes from.

    Odoo already models "on this voucher journal, money may move by this method,
    booked against this account": that is a payment method line, and its
    ``payment_account_id`` is the money side of the entry — the very thing KMITL
    calls หัวจ่าย. So a line that names that account **is** a paying account, and
    a line that does not (the ones Odoo seeds on every bank journal by default)
    is not one and is filtered out of every หัวจ่าย field. What makes a line a
    paying account is that it knows the money's origin, not that it has a bank:
    that is what lets cash be one too.

    All this module adds is what the bank needs and Odoo does not keep here: the
    institute's own bank account (the e-payment file's sending account, and the
    cheque book the register controls) and the cheque print calibration.

    A bank account alone cannot identify a paying account — a current account may
    be transferred from *and* drawn cheques on. The GL account, though, belongs
    to the bank account and not to the pairing: a cheque and a transfer out of
    the same account hit the same GL. Hence the constraint below instead of
    storing it somewhere else and copying it in.
    """

    _inherit = "account.payment.method.line"

    bank_account_id = fields.Many2one(
        comodel_name="res.partner.bank",
        string="Bank Account",
        help="The institute's own bank account the money leaves from. Read by "
        "the bank payment export as the sending account and by the cheque "
        "register as the cheque book. Empty for cash.",
    )
    bank_id = fields.Many2one(
        related="bank_account_id.bank_id",
        string="Bank",
        store=True,
        readonly=True,
        help="Stored so that a payee's own bank can be auto-matched in SQL.",
    )
    acc_number = fields.Char(
        related="bank_account_id.acc_number",
        string="Account Number",
        readonly=True,
    )
    cheque_layout_id = fields.Many2one(
        comodel_name="cheque.layout",
        string="Cheque Layout",
        help="Print calibration for the cheque book drawn on this account.",
    )
    payment_method_code = fields.Char(
        related="payment_method_id.code",
        string="Method Code",
        readonly=True,
        help="Exposed for the form's attrs, which cannot follow a relation.",
    )

    @api.onchange("bank_account_id")
    def _onchange_bank_account_id(self):
        """Offer the GL account this bank account is already booked against.

        A second way of paying out of the same account has to use the same GL, so
        proposing it turns the constraint below into a formality rather than a
        thing to be caught.
        """
        for line in self:
            if line.payment_account_id or not line.bank_account_id:
                continue
            sibling = self.search(
                [
                    ("bank_account_id", "=", line.bank_account_id.id),
                    ("payment_account_id", "!=", False),
                ],
                limit=1,
            )
            line.payment_account_id = sibling.payment_account_id

    @api.constrains("bank_account_id", "payment_account_id", "payment_method_id")
    def _check_paying_account(self):
        """Guard the two things that make a paying account usable.

        Only lines that are paying accounts at all are checked, so the method
        lines Odoo seeds by default and those belonging to payment providers are
        left alone.
        """
        for line in self:
            if not line.payment_account_id:
                continue
            if (
                line.payment_method_id.code in BANKED_METHOD_CODES
                and not line.bank_account_id
            ):
                raise ValidationError(
                    _(
                        "Paying account '%s' pays through a bank, so it needs "
                        "the institute's bank account the money leaves from."
                    )
                    % line.display_name
                )
            if not line.bank_account_id:
                continue
            conflicting = self.search(
                [
                    ("id", "!=", line.id),
                    ("bank_account_id", "=", line.bank_account_id.id),
                    ("payment_account_id", "!=", False),
                    ("payment_account_id", "!=", line.payment_account_id.id),
                ],
                limit=1,
            )
            if conflicting:
                raise ValidationError(
                    _(
                        "Paying accounts on bank account %(bank_account)s must "
                        "book to the same GL account: '%(other)s' uses "
                        "%(other_account)s. Money leaving one bank account "
                        "leaves the same ledger account however it is paid.",
                        bank_account=line.bank_account_id.display_name,
                        other=conflicting.display_name,
                        other_account=(
                            conflicting.payment_account_id.display_name
                        ),
                    )
                )
