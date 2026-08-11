# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AccountPaymentMethodLine(models.Model):
    """Let a payment method line book against a bank account.

    Odoo's ``payment_account_id`` is an *outstanding* account: money is parked
    there when a payment is registered and only reaches the bank account once a
    bank statement is reconciled, so its domain offers current assets and not the
    bank accounts themselves. KMITL runs no bank statements — registering the
    payment *is* the settlement — so the money side of the entry is the bank
    account, and every one of them is ``asset_cash`` in the KMITL chart (215 of
    them, e.g. 1112210004 ธ.ไทยพาณิชย์ /ย่อยเทคโนฯ /SA-088-2-11066-5). None
    could be picked.

    Only the domain is widened. The account was always writable through the ORM —
    a field's domain constrains the dropdown, not ``write()``, which is why the
    install hook could point PV's method lines at the journal's bank account
    while nobody could choose one by hand. This makes the screen agree with what
    the data already does.
    """

    _inherit = "account.payment.method.line"

    # Redeclaring the domain alone keeps every other attribute from core
    # (comodel, string, check_company, ondelete). ``company_id`` is safe to read
    # here: core's own domains on this model already use it, so every view that
    # shows these fields carries it.
    payment_account_id = fields.Many2one(
        domain="[('deprecated', '=', False), "
        "('company_id', '=', company_id), "
        "('account_type', 'in', ('asset_current', 'asset_cash'))]",
    )
