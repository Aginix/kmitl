# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)

# The institute's paying accounts (หัวจ่าย) as given by the treasury office:
# its own bank accounts, the branch each is held at, the GL account each is
# booked against (by chart code) and the way money normally leaves it. A current
# account can be both transferred from and drawn cheques on, so the method here
# is the one in use — a second one is added by hand when it is needed.
#
# Only the bank accounts are seeded. A paying account is a payment method line on
# a *voucher* journal (ใบสำคัญ), and which journal that is differs per database
# and is not knowable here, so the treasury office finishes the setup in
# Finance ▸ Settings ▸ หัวจ่าย.
MAIN_PAYING_ACCOUNTS = [
    {
        "code": "1112210004",
        "bic": "SICOTHBK",
        "acc_number": "088-2-11066-5",
        "branch": "ย่อยเทคโนฯ",
        "method": "kmitl_transfer",
    },
    {
        "code": "1112220015",
        "bic": "SICOTHBK",
        "acc_number": "088-3-00303-1",
        "branch": "ย่อยเทคโนฯ",
        "method": "kmitl_cheque",
    },
    {
        "code": "1112110012",
        "bic": "SICOTHBK",
        "acc_number": "088-2-60881-2",
        "branch": "เทคโนฯ",
        "method": "kmitl_transfer",
    },
    {
        "code": "1112120003",
        "bic": "SICOTHBK",
        "acc_number": "088-3-00005-9",
        "branch": "ย่อยเทคโนฯ",
        "method": "kmitl_transfer",
    },
    {
        "code": "1112120002",
        "bic": "KRTHTHBK",
        "acc_number": "028-6-01583-8",
        "branch": "หัวตะเข้",
        "method": "kmitl_transfer",
    },
    {
        "code": "1112120016",
        "bic": "AYUDTHBK",
        "acc_number": "507-0-00013-4",
        "branch": "ย่อยเทคโนฯ",
        "method": "kmitl_transfer",
    },
    {
        "code": "1112120006",
        "bic": "KASITHBK",
        "acc_number": "036-1-00165-6",
        "branch": "ลาดกระบัง",
        "method": "kmitl_transfer",
    },
]

# The fallback for a payee whose bank is none of the above.
DEFAULT_PAYING_ACCOUNT_CODE = "1112210004"

# Which of the paying accounts each seeded subject may pay from, and whether the
# subject auto-matches by the payee's bank. Auto-match serves each payee from the
# allowed account at their own bank, falling back to the subject's main/fallback
# account; without it every payee pays from that one account.
SUBJECT_PAYING_ACCOUNTS = {
    "finance_kmitl.payment_subject_salary": {
        "codes": ["1112120002"],
        "auto_match": False,
    },
    "finance_kmitl.payment_subject_advance_reimburse": {
        "codes": [
            entry["code"]
            for entry in MAIN_PAYING_ACCOUNTS
            if entry["method"] == "kmitl_transfer"
        ],
        "auto_match": True,
    },
    "finance_kmitl.payment_subject_vendor_direct": {
        "codes": ["1112210004"],
        "auto_match": False,
    },
    "finance_kmitl.payment_subject_utilities": {
        "codes": ["1112220015"],
        "auto_match": False,
    },
}


def _seed_bank_accounts(env, company):
    """Create the institute's own bank accounts, the ones money is paid out of.

    Only the bank accounts: a paying account (หัวจ่าย) is a payment method line
    on a voucher journal, and which journal that is cannot be known here. Returns
    them keyed by the chart code of the GL account each is booked against, which
    is what the treasury office has to put on the method line.

    Idempotent and best-effort: an existing account with the same (sanitized)
    number is reused, and a chart missing the GL code is reported rather than
    failing the install.
    """
    from odoo.addons.base.models.res_bank import sanitize_account_number

    accounts = {}
    Bank = env["res.bank"]
    PartnerBank = env["res.partner.bank"]
    for entry in MAIN_PAYING_ACCOUNTS:
        gl_account = env["account.account"].search(
            [("code", "=", entry["code"]), ("company_id", "=", company.id)],
            limit=1,
        )
        if not gl_account:
            _logger.warning(
                "finance_kmitl: account code %s not found for %s; its paying "
                "account has to be set up by hand.",
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
        accounts[entry["code"]] = bank_account
    return accounts


def _find_paying_accounts(env, company, bank_accounts):
    """Match each seeded bank account to its paying account, if one exists yet.

    Re-runnable on purpose: the first install finds none and says so, and once
    the treasury office has created the method lines, running the hook again
    (module upgrade with a reinstall) binds the subjects without anyone editing
    them by hand.
    """
    MethodLine = env["account.payment.method.line"]
    paying_accounts = {}
    missing = []
    for entry in MAIN_PAYING_ACCOUNTS:
        bank_account = bank_accounts.get(entry["code"])
        if not bank_account:
            continue
        line = MethodLine.search(
            [
                ("bank_account_id", "=", bank_account.id),
                ("payment_account_id", "!=", False),
                ("payment_method_id.code", "=", entry["method"]),
                ("company_id", "=", company.id),
            ],
            limit=1,
        )
        if line:
            paying_accounts[entry["code"]] = line
        else:
            missing.append(
                "%s (%s, GL %s)"
                % (bank_account.display_name, entry["method"], entry["code"])
            )
    if missing:
        _logger.warning(
            "finance_kmitl: no paying account yet for %s — create one payment "
            "method line per account on the right voucher journal (ใบสำคัญ) in "
            "Finance ▸ Settings ▸ หัวจ่าย, naming its bank account and GL "
            "account. Until then the disbursement audit will refuse the "
            "requests that need them.",
            "; ".join(missing),
        )
    return paying_accounts


def _setup_default_paying_account(env, company, paying_accounts):
    """Point the company at the institute-wide fallback paying account."""
    account = paying_accounts.get(DEFAULT_PAYING_ACCOUNT_CODE)
    if account and not company.default_paying_account_id:
        company.default_paying_account_id = account.id


def _setup_subject_paying_accounts(env, paying_accounts):
    """Give each seeded subject the paying accounts it may pay from.

    Subjects an administrator already configured are left untouched.
    """
    for xmlid, config in SUBJECT_PAYING_ACCOUNTS.items():
        subject = env.ref(xmlid, raise_if_not_found=False)
        if not subject or subject.allowed_paying_account_ids:
            continue
        allowed = [
            paying_accounts[code].id
            for code in config["codes"]
            if paying_accounts.get(code)
        ]
        if not allowed:
            continue
        default = paying_accounts.get(DEFAULT_PAYING_ACCOUNT_CODE)
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
        bank_accounts = _seed_bank_accounts(env, company)
        paying_accounts = _find_paying_accounts(env, company, bank_accounts)
        _setup_default_paying_account(env, company, paying_accounts)
        if company == env.ref("base.main_company", raise_if_not_found=False):
            _setup_subject_paying_accounts(env, paying_accounts)


def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    setup_paying_accounts(env)
