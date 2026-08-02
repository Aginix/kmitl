# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)

# KMITL's fallback paying account (หัวจ่ายตั้งต้น): a payee whose bank is not
# one of the main paying banks is paid from this one. Identified by chart code
# rather than an external id, because the chart publishes stable xmlids only
# for the accounts other modules reference by name.
DEFAULT_PAYING_ACCOUNT_CODE = "1112210004"
DEFAULT_PAYING_ACCOUNT = {
    "bank_bic": "SICOTHBK",
    "acc_number": "088-2-11066-5",
}


def _setup_default_paying_account(env, company):
    """Flag the institute's fallback paying account and point the company at it.

    Idempotent and best-effort: an account already flagged keeps its own bank
    and number, and a chart without that code simply leaves the company default
    empty for an administrator to set.
    """
    account = env["account.account"].search(
        [
            ("code", "=", DEFAULT_PAYING_ACCOUNT_CODE),
            ("company_id", "=", company.id),
        ],
        limit=1,
    )
    if not account:
        _logger.warning(
            "finance_kmitl: account code %s not found for %s; set the default "
            "paying account manually.",
            DEFAULT_PAYING_ACCOUNT_CODE,
            company.display_name,
        )
        return
    if not account.is_paying_account:
        vals = {"is_paying_account": True}
        if not account.paying_acc_number:
            vals["paying_acc_number"] = DEFAULT_PAYING_ACCOUNT["acc_number"]
        bank = env["res.bank"].search(
            [("bic", "=", DEFAULT_PAYING_ACCOUNT["bank_bic"])], limit=1
        )
        if bank and not account.paying_bank_id:
            vals["paying_bank_id"] = bank.id
        account.write(vals)
    if not company.default_paying_account_id:
        company.default_paying_account_id = account.id


def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    for company in env["res.company"].search([]):
        _setup_default_paying_account(env, company)
