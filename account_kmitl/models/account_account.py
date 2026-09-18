# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class AccountAccount(models.Model):
    """Links a GL account to the institute's own bank account it is booked
    against, independent of whether it is ever a หัวจ่าย.

    ``account.payment.method.line.bank_account_id`` already carries this for
    a paying account, but a GL account can appear in other roles that never
    become one — an intermediate account on a cash-movement route
    (disbursement_cash_movement_kmitl), for one — and those have no payment
    method line to read it from.
    """

    _inherit = "account.account"

    kmitl_bank_account_id = fields.Many2one(
        comodel_name="res.partner.bank",
        string="Bank Account",
        help="The institute's own bank account this GL account is booked "
        "against, when it is a cash/bank account. Set independently of any "
        "หัวจ่าย this account may also be, so a GL account can be named "
        "compactly (bank + account number) wherever that account only, and "
        "not the paying account, matters.",
    )
