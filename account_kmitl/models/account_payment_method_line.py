# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

# The KMITL methods that move money through a bank and therefore need one.
BANKED_METHOD_CODES = ("kmitl_transfer", "kmitl_cheque")


class AccountPaymentMethodLine(models.Model):
    """หัวจ่าย — a payment method line that knows where the money comes from.

    Odoo already models "on this voucher journal, money may move by this method,
    booked against this account": that is a payment method line, and its
    ``payment_account_id`` is the money side of the entry — the very thing KMITL
    calls หัวจ่าย. So it needs no model of its own; all that is missing is what
    the bank needs and Odoo does not keep here — the institute's own bank
    account, which the e-payment file carries as its sending account and the
    cheque register uses as the cheque book. Cash has none, which is fine: a
    paying account is defined by knowing the money's origin, not by having a bank.

    A bank account alone cannot identify a paying account — a current account may
    be transferred from *and* drawn cheques on. The GL account, though, belongs to
    the bank account rather than to the pairing: a cheque and a transfer out of
    the same account hit the same GL, because money leaving one bank account
    leaves one ledger account however it is paid. Hence the constraint below.

    **Where the "a bank method needs a bank account" rule lives.** Not here: the
    install seeds every bank journal with the KMITL methods and points them at
    the journal's default account before the paying accounts are shaped, so a
    model-level constraint would fire on rows that are not paying accounts at
    all. It is enforced where it can be acted on instead — the disbursement audit
    refuses a payee routed through a bank-less paying account, and the bank export
    refuses a file with no sending account. This form warns as soon as it can.
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

    @api.onchange("payment_method_id", "payment_account_id")
    def _onchange_warn_missing_bank_account(self):
        """Warn — never block — a paying account that pays through a bank
        without naming one. See the class docstring for why this is not a
        constraint."""
        self.ensure_one()
        if (
            self.payment_account_id
            and self.payment_method_id.code in BANKED_METHOD_CODES
            and not self.bank_account_id
        ):
            return {
                "warning": {
                    "title": _("Paying account without a bank account"),
                    "message": _(
                        "%s pays through a bank, so it needs the institute's "
                        "bank account the money leaves from. Without it the "
                        "e-payment file has no sending account and the "
                        "disbursement audit will refuse the payees routed "
                        "through it."
                    )
                    % (self.payment_method_id.name or ""),
                }
            }

    @api.constrains("bank_account_id", "payment_account_id")
    def _check_paying_account(self):
        """Guard the two things that make a paying account bookable.

        Only lines that name a GL account are checked, so the ones belonging to
        payment providers are left alone.
        """
        for line in self:
            account = line.payment_account_id
            if not account:
                continue
            if account.account_type in ("asset_receivable", "liability_payable"):
                raise ValidationError(
                    _(
                        "%s cannot be a paying account: Odoo classifies a "
                        "payment's lines by account type and tests the money "
                        "side first, so a receivable/payable account there "
                        "would swallow the counterpart line and make the "
                        "payment unsavable."
                    )
                    % account.display_name
                )
            if not line.bank_account_id:
                continue
            conflicting = self.search(
                [
                    ("id", "!=", line.id),
                    ("bank_account_id", "=", line.bank_account_id.id),
                    ("payment_account_id", "!=", False),
                    ("payment_account_id", "!=", account.id),
                ],
                limit=1,
            )
            if conflicting:
                raise ValidationError(
                    _(
                        "Every paying account on %(bank)s must be booked "
                        "against the same GL account — money leaving one bank "
                        "account leaves one ledger account however it is paid. "
                        "%(other)s already uses %(account)s.",
                        bank=line.bank_account_id.display_name,
                        other=conflicting.display_name,
                        account=conflicting.payment_account_id.display_name,
                    )
                )
