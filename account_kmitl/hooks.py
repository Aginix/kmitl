import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def _create_journals(env, company):
    """Create KMITL journals after chart of accounts is loaded."""
    Account = env["account.account"]

    def get_account(code):
        return Account.search([("code", "=", code), ("company_id", "=", company.id)], limit=1)

    journals_data = [
        {
            "name": "สมุดรายวันทั่วไป",
            "code": "JV",
            "type": "general",
            "company_id": company.id,
            "sequence": 10,
        },
        {
            "name": "สมุดรายวันจ่าย",
            "code": "PV",
            "type": "bank",
            "company_id": company.id,
            "default_account_id": get_account("1112210004").id or False,
            "sequence": 20,
        },
        {
            "name": "สมุดรายวันรับ",
            "code": "RV",
            "type": "bank",
            "company_id": company.id,
            "default_account_id": get_account("1112210004").id or False,
            "sequence": 30,
        },
        {
            "name": "สมุดรายวันขาย",
            "code": "SV",
            "type": "sale",
            "company_id": company.id,
            "default_account_id": get_account("4000000000").id or False,
            "sequence": 40,
        },
        {
            "name": "สมุดรายวันซื้อ",
            "code": "UV",
            "type": "purchase",
            "company_id": company.id,
            "default_account_id": get_account("5000000000").id or False,
            "sequence": 50,
        },
    ]

    Journal = env["account.journal"]
    for data in journals_data:
        existing = Journal.search(
            [("code", "=", data["code"]), ("company_id", "=", company.id)], limit=1
        )
        if not existing:
            Journal.create(data)

    # Set payment_account_id on bank journal payment method lines
    payment_account = get_account("1112210004")
    if payment_account:
        bank_journals = Journal.search(
            [
                ("company_id", "=", company.id),
                ("code", "in", ("PV", "RV")),
            ]
        )
        payment_method_lines = (
            bank_journals.inbound_payment_method_line_ids
            + bank_journals.outbound_payment_method_line_ids
        )
        payment_method_lines.payment_account_id = payment_account


def _deactivate_default_journals(env, company):
    """Deactivate all non-KMITL journals created by the chart of accounts loader."""
    kmitl_codes = ("JV", "PV", "RV", "SV", "UV")
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
