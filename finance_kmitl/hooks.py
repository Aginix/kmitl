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

# Which of the main accounts each seeded subject may pay from, and whether the
# subject auto-matches by the payee's bank. Auto-match serves each payee from
# the allowed account at their own bank, falling back to the subject's
# main/fallback account; without it every payee pays from that one account.
SUBJECT_PAYING_ACCOUNTS = {
    "finance_kmitl.payment_subject_salary": {
        "codes": ["1112210010"],
        "auto_match": False,
    },
    "finance_kmitl.payment_subject_advance_reimburse": {
        "codes": [entry["code"] for entry in MAIN_PAYING_ACCOUNTS],
        "auto_match": True,
    },
    "finance_kmitl.payment_subject_vendor_direct": {
        "codes": ["1112210004"],
        "auto_match": False,
    },
    "finance_kmitl.payment_subject_utilities": {
        "codes": ["1112210004"],
        "auto_match": False,
    },
}


def _seed_main_paying_accounts(env, company):
    """Create the main paying accounts (หัวจ่าย) — the institute's own bank
    accounts paired with **เงินโอน** — and bind each to the GL account its
    transfers are booked against (matched by chart code).

    Only the transfer pairs are seeded. A cheque pair is booked against a
    separate "เช็คจ่าย" account per bank, and that account cannot be guessed
    from a chart code here: the treasury office creates those in
    Finance ▸ Settings ▸ หัวจ่าย.

    Idempotent and best-effort: an existing bank account with the same
    (sanitized) number is reused and an existing paying account keeps whatever
    the treasury office configured; a chart without the GL code skips that
    account with a warning rather than failing the install.
    """
    from odoo.addons.base.models.res_bank import sanitize_account_number

    accounts = {}
    Bank = env["res.bank"]
    PartnerBank = env["res.partner.bank"]
    PayingAccount = env["kmitl.paying.account"]
    transfer_type = env.ref(
        "finance_kmitl.payment_type_normal_outbound", raise_if_not_found=False
    )
    if not transfer_type:
        _logger.warning(
            "finance_kmitl: the เงินโอน payment type is missing; paying "
            "accounts must be created by hand."
        )
        return accounts
    provisional = []
    for entry in MAIN_PAYING_ACCOUNTS:
        gl_account = env["account.account"].search(
            [("code", "=", entry["code"]), ("company_id", "=", company.id)],
            limit=1,
        )
        if not gl_account:
            _logger.warning(
                "finance_kmitl: account code %s not found for %s; add its "
                "paying account by hand.",
                entry["code"],
                company.display_name,
            )
            continue
        bank = Bank.search([("bic", "=", entry["bic"])], limit=1)
        bank_account = PartnerBank.search(
            [
                ("partner_id", "=", company.partner_id.id),
                (
                    "sanitized_acc_number",
                    "=",
                    sanitize_account_number(entry["acc_number"]),
                ),
            ],
            limit=1,
        )
        if not bank_account:
            bank_account = PartnerBank.create(
                {
                    "partner_id": company.partner_id.id,
                    "acc_number": entry["acc_number"],
                    "bank_id": bank.id if bank else False,
                    "acc_holder_name": company.name,
                }
            )
        if not bank_account.bank_id and bank:
            bank_account.bank_id = bank.id
        paying_account = PayingAccount.search(
            [
                ("bank_account_id", "=", bank_account.id),
                ("payment_type_id", "=", transfer_type.id),
                ("company_id", "=", company.id),
            ],
            limit=1,
        ) or PayingAccount.create(
            {
                "bank_account_id": bank_account.id,
                "payment_type_id": transfer_type.id,
                "payment_account_id": gl_account.id,
                "company_id": company.id,
            }
        )
        accounts[entry["code"]] = paying_account
        if not entry["confirmed"]:
            provisional.append(paying_account.display_name)
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
    transfer_type = env.ref(
        "finance_kmitl.payment_type_normal_outbound", raise_if_not_found=False
    )
    for xmlid, config in SUBJECT_PAYING_ACCOUNTS.items():
        subject = env.ref(xmlid, raise_if_not_found=False)
        if not subject or subject.allowed_paying_account_ids:
            continue
        # Only transfer paying accounts are seeded, so a subject paid another
        # way is left for the treasury office rather than bound to an account
        # that pays the wrong way out of the wrong GL.
        if subject.default_payment_type_id != transfer_type:
            _logger.warning(
                "finance_kmitl: subject '%s' is paid by %s — create its "
                "paying account in Finance ▸ Settings ▸ หัวจ่าย and bind it "
                "to the subject.",
                subject.name,
                subject.default_payment_type_id.name,
            )
            continue
        allowed = [
            accounts[code].id
            for code in config["codes"]
            if accounts.get(code)
        ]
        if not allowed:
            continue
        default = accounts.get(DEFAULT_PAYING_ACCOUNT_CODE)
        vals = {
            "allowed_paying_account_ids": [(6, 0, allowed)],
            "auto_match_payee_bank": config["auto_match"],
        }
        if default and default.id in allowed:
            vals["default_paying_account_id"] = default.id
        else:
            vals["default_paying_account_id"] = allowed[0]
        subject.write(vals)


def setup_paying_accounts(env):
    for company in env["res.company"].search([]):
        accounts = _seed_main_paying_accounts(env, company)
        _setup_default_paying_account(env, company, accounts)
        if company == env.ref("base.main_company", raise_if_not_found=False):
            _setup_subject_paying_accounts(env, accounts)


def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    setup_paying_accounts(env)
