# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)

# KMITL's main paying accounts (หัวจ่ายหลัก), one per bank. A payee banking
# with one of these is paid from the account held there; everyone else is paid
# from the fallback below.
#
# They are identified by chart code — the chart publishes stable external ids
# only for the accounts other modules reference by name — and they all sit in
# the same 11122100xx group (เงินฝากธนาคาร - เงินรายได้-ออมทรัพย์) at the
# ย่อยเทคโนฯ branch.
#
# ``confirmed`` marks the one the treasury office named. The other three are
# the closest match in that same group and are a starting point only: the
# treasury office should confirm or replace them in
# Finance ▸ Settings ▸ หัวจ่าย.
MAIN_PAYING_ACCOUNTS = [
    {
        "code": "1112210004",
        "bic": "SICOTHBK",
        "acc_number": "088-2-11066-5",
        "confirmed": True,
    },
    {
        "code": "1112210010",
        "bic": "KRTHTHBK",
        "acc_number": "693-0-00315-8",
        "confirmed": False,
    },
    {
        "code": "1112210017",
        "bic": "KASITHBK",
        "acc_number": "631-2-01778-2",
        "confirmed": False,
    },
    {
        "code": "1112210009",
        "bic": "AYUDTHBK",
        "acc_number": "507-1-00001-4",
        "confirmed": False,
    },
]

# The fallback for a payee whose bank is none of the above.
DEFAULT_PAYING_ACCOUNT_CODE = "1112210004"

# Which of the main accounts each seeded subject may pay from. A subject that
# lists one account always uses it; one that lists several serves each payee
# from the account at their own bank.
SUBJECT_PAYING_ACCOUNTS = {
    "finance_kmitl.payment_subject_salary": ["1112210010"],
    "finance_kmitl.payment_subject_advance_reimburse": [
        entry["code"] for entry in MAIN_PAYING_ACCOUNTS
    ],
    "finance_kmitl.payment_subject_vendor_direct": ["1112210004"],
    "finance_kmitl.payment_subject_utilities": ["1112210004"],
}


def _flag_main_paying_accounts(env, company):
    """Flag the main paying accounts and record their bank / account number.

    Idempotent and best-effort: an account already flagged keeps whatever the
    treasury office configured, and a chart without a code is skipped with a
    warning rather than failing the install.
    """
    accounts = {}
    Bank = env["res.bank"]
    provisional = []
    for entry in MAIN_PAYING_ACCOUNTS:
        account = env["account.account"].search(
            [("code", "=", entry["code"]), ("company_id", "=", company.id)],
            limit=1,
        )
        if not account:
            _logger.warning(
                "finance_kmitl: account code %s not found for %s; add its "
                "paying account by hand.",
                entry["code"],
                company.display_name,
            )
            continue
        accounts[entry["code"]] = account
        if account.is_paying_account:
            continue
        vals = {"is_paying_account": True}
        if not account.paying_acc_number:
            vals["paying_acc_number"] = entry["acc_number"]
        if not account.paying_bank_id:
            bank = Bank.search([("bic", "=", entry["bic"])], limit=1)
            if bank:
                vals["paying_bank_id"] = bank.id
            else:
                _logger.warning(
                    "finance_kmitl: no bank with BIC %s; set the bank on "
                    "paying account %s by hand.",
                    entry["bic"],
                    account.display_name,
                )
        account.write(vals)
        if not entry["confirmed"]:
            provisional.append(account.display_name)
    if provisional:
        _logger.warning(
            "finance_kmitl: provisional paying accounts seeded — have the "
            "treasury office confirm or replace them in Finance ▸ Settings ▸ "
            "หัวจ่าย: %s",
            ", ".join(provisional),
        )
    return accounts


def _setup_default_paying_account(env, company, accounts):
    """Point the company at the institute-wide fallback paying account."""
    account = accounts.get(DEFAULT_PAYING_ACCOUNT_CODE)
    if account and not company.default_paying_account_id:
        company.default_paying_account_id = account.id


def _setup_subject_paying_accounts(env, accounts):
    """Give each seeded subject the accounts it may pay from.

    Subjects an administrator already configured are left untouched.
    """
    for xmlid, codes in SUBJECT_PAYING_ACCOUNTS.items():
        subject = env.ref(xmlid, raise_if_not_found=False)
        if not subject or subject.allowed_paying_account_ids:
            continue
        allowed = [
            accounts[code].id for code in codes if accounts.get(code)
        ]
        if not allowed:
            continue
        default = accounts.get(DEFAULT_PAYING_ACCOUNT_CODE)
        vals = {"allowed_paying_account_ids": [(6, 0, allowed)]}
        if default and default.id in allowed:
            vals["default_paying_account_id"] = default.id
        else:
            vals["default_paying_account_id"] = allowed[0]
        subject.write(vals)


def setup_paying_accounts(env):
    for company in env["res.company"].search([]):
        accounts = _flag_main_paying_accounts(env, company)
        _setup_default_paying_account(env, company, accounts)
        if company == env.ref("base.main_company", raise_if_not_found=False):
            _setup_subject_paying_accounts(env, accounts)


def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    setup_paying_accounts(env)
