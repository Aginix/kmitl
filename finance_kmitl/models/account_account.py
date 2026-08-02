# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AccountAccount(models.Model):
    """Mark the GL accounts KMITL actually pays money out of (หัวจ่าย).

    In the KMITL chart one GL account is one real bank account — the bank and
    the account number are already part of its name (e.g. "ธ.กรุงไทย /ลาดกระบัง
    / SA-028-1-03878-3"). Rather than duplicating that into a separate master
    data model, the accounting office flags the accounts that serve as paying
    accounts and records the bank / account number as proper fields, so the
    bank export and the cheque register can read them.

    Cash accounts qualify too: KMITL types cash-in-hand as ``asset_current``
    and bank accounts as ``asset_cash``, so the flag — not the account type —
    is what makes an account payable-from.
    """

    _inherit = "account.account"

    is_paying_account = fields.Boolean(
        string="Paying Account (หัวจ่าย)",
        help="Money can be paid out of this account. Paying accounts are the "
        "ones offered on a payment subject and picked per disbursement line.",
    )
    paying_bank_id = fields.Many2one(
        comodel_name="res.bank",
        string="Bank",
        help="The bank holding this account. Used to build the e-payment file "
        "and to identify the cheque book.",
    )
    paying_acc_number = fields.Char(
        string="Account Number",
        help="The account number at the bank, as the bank expects it in the "
        "e-payment file.",
    )
    cheque_layout_id = fields.Many2one(
        comodel_name="cheque.layout",
        string="Cheque Layout",
        help="Print calibration for the cheque book drawn on this account.",
    )

    @api.constrains("is_paying_account", "account_type")
    def _check_paying_account_type(self):
        """A paying account may not be a receivable/payable account.

        Odoo classifies a payment's journal items by account, testing the money
        side before the counterpart: an account that is both would swallow the
        payable line and make the payment unsavable.
        """
        for account in self:
            if account.is_paying_account and account.account_type in (
                "asset_receivable",
                "liability_payable",
            ):
                raise ValidationError(
                    _(
                        "'%s' is a receivable/payable account, so it cannot "
                        "also be a paying account (หัวจ่าย)."
                    )
                    % account.display_name
                )

    @api.constrains("is_paying_account", "paying_bank_id", "paying_acc_number")
    def _check_paying_account(self):
        """A paying account held at a bank must carry its account number.

        Cash accounts have no bank and no number, so the check only applies
        once a bank is set.
        """
        for account in self:
            if not account.is_paying_account:
                continue
            if account.paying_bank_id and not account.paying_acc_number:
                raise ValidationError(
                    _(
                        "Paying account '%s' is held at a bank, so it needs "
                        "its account number."
                    )
                    % account.display_name
                )
