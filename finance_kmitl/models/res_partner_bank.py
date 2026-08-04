# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ResPartnerBank(models.Model):
    """Mark the institute's bank accounts money is paid out of (หัวจ่าย).

    A paying account is a real bank account, so it lives on the model that
    already carries the bank and the account number — ``res.partner.bank`` on
    the company's partner — and only gains what a bank account does not know:
    which GL account the payment is booked against, and the cheque book's
    print calibration.

    Cash counts too: a "CASH"-numbered record with no bank, pointing at the
    cash GL account, makes เงินสด a paying account without a special case.
    """

    _inherit = "res.partner.bank"

    is_paying_account = fields.Boolean(
        string="Paying Account (หัวจ่าย)",
        help="Money can be paid out of this account. Paying accounts are the "
        "ones offered on a payment subject and picked per disbursement line.",
    )
    payment_account_id = fields.Many2one(
        comodel_name="account.account",
        string="GL Account",
        check_company=True,
        domain="[('deprecated', '=', False), "
        "('account_type', 'not in', ('asset_receivable', 'liability_payable'))]",
        help="The general-ledger account a payment from this bank account is "
        "booked against (KMITL settles a payable in one step, so this is the "
        "money side of the entry).",
    )
    cheque_layout_id = fields.Many2one(
        comodel_name="cheque.layout",
        string="Cheque Layout",
        help="Print calibration for the cheque book drawn on this account.",
    )

    @api.constrains("is_paying_account", "payment_account_id")
    def _check_paying_account(self):
        """A paying account must know where to book the money.

        The GL account may not be a receivable/payable one: Odoo classifies a
        payment's journal items by account and tests the money side first, so
        such an account would swallow the counterpart line and make the
        payment unsavable.
        """
        for bank_account in self:
            if not bank_account.is_paying_account:
                continue
            if not bank_account.payment_account_id:
                raise ValidationError(
                    _(
                        "Paying account '%s' needs the GL account its "
                        "payments are booked against."
                    )
                    % bank_account.display_name
                )
            if bank_account.payment_account_id.account_type in (
                "asset_receivable",
                "liability_payable",
            ):
                raise ValidationError(
                    _(
                        "The GL account of paying account '%s' cannot be a "
                        "receivable/payable account."
                    )
                    % bank_account.display_name
                )
