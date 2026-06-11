import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)

# Journal master data. ``account`` is the account code used as the journal's
# default account (resolved after the chart is loaded); ``None`` when the
# journal has no default account.
JOURNALS = [
    {"xmlid": "journal_jv", "code": "JV", "name": "สมุดรายวันทั่วไป", "type": "general", "sequence": 10, "account": None},
    {"xmlid": "journal_pv", "code": "PV", "name": "สมุดรายวันจ่าย", "type": "bank", "sequence": 20, "account": "1112210004"},
    {"xmlid": "journal_rv", "code": "RV", "name": "สมุดรายวันรับ", "type": "bank", "sequence": 30, "account": "1112210004"},
    {"xmlid": "journal_ar", "code": "AR", "name": "สมุดรายวันขาย", "type": "sale", "sequence": 40, "account": "4000000000"},
    {"xmlid": "journal_ap", "code": "AP", "name": "สมุดรายวันซื้อ", "type": "purchase", "sequence": 50, "account": "5000000000"},
]

# Account used as payment_account_id on the bank journals' payment method lines.
BANK_PAYMENT_ACCOUNT_CODE = "1112210004"


def _create_journals(env, company):
    """Create KMITL journals after the chart of accounts is loaded.

    Journals are created here (not via XML data files) because a bank journal
    created before the chart exists would auto-create a stray liquidity account
    and break ``chart._load``. Each journal is registered with a stable external
    id so other modules can reference it via ``ref``. Idempotent: existing
    journals are reused rather than duplicated.
    """
    Account = env["account.account"]
    Journal = env["account.journal"]

    def get_account(code):
        account = Account.search(
            [("code", "=", code), ("company_id", "=", company.id)], limit=1
        )
        if not account:
            _logger.warning(
                "account_kmitl: account code %s not found for company %s; "
                "leaving journal default account empty.",
                code,
                company.display_name,
            )
        return account

    for data in JOURNALS:
        journal = Journal.search(
            [("code", "=", data["code"]), ("company_id", "=", company.id)], limit=1
        )
        if not journal:
            vals = {
                "name": data["name"],
                "code": data["code"],
                "type": data["type"],
                "company_id": company.id,
                "sequence": data["sequence"],
            }
            if data["account"]:
                vals["default_account_id"] = get_account(data["account"]).id or False
            journal = Journal.create(vals)
        env["ir.model.data"]._update_xmlids(
            [
                {
                    "xml_id": "account_kmitl.%s" % data["xmlid"],
                    "record": journal,
                    "noupdate": True,
                }
            ]
        )

    # Set payment_account_id on bank journal payment method lines
    payment_account = get_account(BANK_PAYMENT_ACCOUNT_CODE)
    if payment_account:
        bank_codes = [j["code"] for j in JOURNALS if j["type"] == "bank"]
        bank_journals = Journal.search(
            [
                ("company_id", "=", company.id),
                ("code", "in", bank_codes),
            ]
        )
        payment_method_lines = (
            bank_journals.inbound_payment_method_line_ids
            + bank_journals.outbound_payment_method_line_ids
        )
        payment_method_lines.payment_account_id = payment_account


def _deactivate_default_journals(env, company):
    """Deactivate all non-KMITL journals created by the chart of accounts loader."""
    kmitl_codes = tuple(j["code"] for j in JOURNALS)
    journals_to_deactivate = env["account.journal"].search(
        [
            ("company_id", "=", company.id),
            ("code", "not in", kmitl_codes),
        ]
    )
    journals_to_deactivate.write({"active": False})


def _create_withholding_taxes(env, company):
    """Create KMITL withholding tax records after chart of accounts is loaded."""
    Account = env["account.account"]

    def get_account(code):
        return Account.search(
            [("code", "=", code), ("company_id", "=", company.id)], limit=1
        )

    # Mark WHT accounts
    for code in ("2120000010", "2120000099"):
        account = get_account(code)
        if account and not account.wht_account:
            account.wht_account = True

    wht_data = [
        {
            "name": "ภาษี หัก ณ ที่จ่ายบุคคลธรรมดา",
            "amount": 1.0,
            "account_id": get_account("2120000010").id,
            "income_tax_form": "pnd1",
            "wht_cert_income_type": "1",
        },
        {
            "name": "ภาษี หัก ณ ที่จ่ายนิติบุคคลจากหน่วยงานเอกชน",
            "amount": 1.0,
            "account_id": get_account("2120000099").id,
            "income_tax_form": "pnd53",
            "wht_cert_income_type": "5",
        },
    ]

    WHT = env["account.withholding.tax"]
    for data in wht_data:
        existing = WHT.search(
            [("name", "=", data["name"]), ("company_id", "=", company.id)], limit=1
        )
        if not existing:
            WHT.create({**data, "company_id": company.id})


def _purge_generic_accounting_demo(env, company):
    """Remove Odoo's generic accounting demo data before loading the KMITL chart.

    When installing with demo data, ``l10n_th`` (a dependency) auto-loads its
    own chart onto the main company and posts demo invoices/payments. Those
    entries make ``account.chart.template.existing_accounting()`` truthy, so
    ``_load`` raises a UserError instead of replacing the chart.

    Safety: this runs in account_kmitl's ``post_init_hook`` -- once, at the very
    moment the KMITL chart is first installed. The KMITL chart does not exist on
    the company yet, so every accounting entry present here is by definition the
    auto-generated demo data, never real user-entered accounting. We therefore
    only act when the database was built *with* demo data; on a production
    (no-demo) install there is nothing to clean and this is a no-op.

    Deleting the moves cascades to their payments and bank statement lines
    (``move_id`` ``ondelete='cascade'``); the now-empty statements are removed
    too.
    """
    if not env.ref("base.module_account").demo:
        return

    moves = env["account.move"].sudo().search([("company_id", "=", company.id)])
    if moves:
        moves.with_context(force_delete=True).unlink()
    env["account.bank.statement"].sudo().search(
        [("company_id", "=", company.id)]
    ).unlink()
    if moves:
        _logger.info(
            "account_kmitl: purged %d generic accounting demo move(s) on %s "
            "before loading the KMITL chart.",
            len(moves),
            company.display_name,
        )


def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    company = env.ref("base.main_company")
    _purge_generic_accounting_demo(env, company)
    env.ref("account_kmitl.chart")._load(company)
    _create_journals(env, company)
    _deactivate_default_journals(env, company)
    _create_withholding_taxes(env, company)
