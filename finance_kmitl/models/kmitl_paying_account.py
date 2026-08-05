# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class KmitlPayingAccount(models.Model):
    """หัวจ่าย — one of the institute's bank accounts paired with the way money
    leaves it.

    A paying account used to be the bank account itself, flagged. That could not
    express what KMITL's chart actually does: a cheque drawn on the KTB account
    is booked against "เช็คจ่าย-KTB", not against the KTB bank account, because
    the money does not leave the bank until the cheque clears weeks later. The
    GL account therefore belongs to the *pair* (bank account × payment type),
    not to either one alone.

    The bank account stays where it was — on ``res.partner.bank``, the company's
    own partner — so the bank, the account number and the BIC are still read
    from the model that natively carries them (the bank export and the cheque
    register do exactly that). This model adds only what the pair knows: which
    GL account the payment is booked against, and the cheque book's print
    calibration.

    Cash counts too: a bank-less "CASH" account paired with the cash payment
    type makes เงินสด a paying account without a special case.

    See ``docs/adr/0001-paying-account-pairs-a-bank-account-with-a-method.md``.
    """

    _name = "kmitl.paying.account"
    _description = "KMITL Paying Account (หัวจ่าย)"
    _order = "bank_account_id, payment_type_id"
    _check_company_auto = True

    bank_account_id = fields.Many2one(
        comodel_name="res.partner.bank",
        string="Bank Account",
        required=True,
        ondelete="cascade",
        help="The institute's own bank account the money leaves from. It "
        "carries the bank, the account number and the BIC.",
    )
    payment_type_id = fields.Many2one(
        comodel_name="kmitl.payment.type",
        string="Payment Method",
        required=True,
        domain="[('direction', '=', 'outbound')]",
        help="วิธีจ่าย — how money leaves this account (เงินโอน / เช็ค / "
        "เงินสด). The same bank account can appear once per method, each with "
        "its own GL account.",
    )
    payment_account_id = fields.Many2one(
        comodel_name="account.account",
        string="GL Account",
        required=True,
        check_company=True,
        domain="[('deprecated', '=', False), "
        "('account_type', 'not in', ('asset_receivable', 'liability_payable'))]",
        help="The general-ledger account a payment of this method from this "
        "bank account is booked against (KMITL settles a payable in one step, "
        "so this is the money side of the entry).",
    )
    cheque_layout_id = fields.Many2one(
        comodel_name="cheque.layout",
        string="Cheque Layout",
        help="Print calibration for the cheque book drawn on this account.",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )
    active = fields.Boolean(default=True)

    # Stored so auto-matching a payee's bank and the export's sending-account
    # grouping can filter in SQL rather than in Python.
    bank_id = fields.Many2one(
        related="bank_account_id.bank_id",
        string="Bank",
        store=True,
        readonly=True,
    )
    acc_number = fields.Char(
        related="bank_account_id.acc_number",
        string="Account Number",
        readonly=True,
    )
    is_cheque = fields.Boolean(
        related="payment_type_id.is_cheque",
        string="Paid by Cheque",
        readonly=True,
    )
    is_cash = fields.Boolean(
        related="payment_type_id.is_cash",
        string="Paid in Cash",
        readonly=True,
    )

    _sql_constraints = [
        (
            "bank_account_method_uniq",
            "unique(bank_account_id, payment_type_id)",
            "A bank account can only have one paying account per payment "
            "method.",
        ),
    ]

    def name_get(self):
        """Read the method in the same breath as the account.

        The auditor picks one field and thereby settles both which account the
        money leaves and how — so the label has to say both.
        """
        return [
            (
                account.id,
                "%s (%s)" % (
                    account.bank_account_id.display_name,
                    account.payment_type_id.name or "",
                ),
            )
            for account in self
        ]

    @api.constrains("payment_account_id")
    def _check_payment_account(self):
        """The GL account may not be a receivable/payable one: Odoo classifies a
        payment's journal items by account and tests the money side first, so
        such an account would swallow the counterpart line and make the payment
        unsavable.
        """
        for paying_account in self:
            if paying_account.payment_account_id.account_type in (
                "asset_receivable",
                "liability_payable",
            ):
                raise ValidationError(
                    _(
                        "The GL account of paying account '%s' cannot be a "
                        "receivable/payable account."
                    )
                    % paying_account.display_name
                )
