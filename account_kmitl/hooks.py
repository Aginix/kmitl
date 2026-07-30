import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)

# Journal master data. ``account`` is the account code used as the journal's
# default account (resolved after the chart is loaded); ``None`` when the
# journal has no default account. Bank journals also point their payment method
# lines at that same default account.
JOURNALS = [
    {"xmlid": "journal_jv", "code": "JV", "name": "ใบสำคัญทั่วไป", "type": "general", "sequence": 10, "account": None},
    {"xmlid": "journal_pv", "code": "PV", "name": "ใบสำคัญจ่าย", "type": "bank", "sequence": 20, "account": "1112210004"},
    {"xmlid": "journal_pvr", "code": "PVR", "name": "ใบสำคัญส่งคืนลูกหนี้เงินยืม", "type": "bank", "sequence": 30, "account": "1112000006"},
    {"xmlid": "journal_rv", "code": "RV", "name": "ใบสำคัญรับ", "type": "bank", "sequence": 40, "account": "1112210004"},
    {"xmlid": "journal_par", "code": "PAR", "name": "ใบสำคัญจ่ายลูกหนี้เงินยืม", "type": "bank", "sequence": 50, "account": "1112110004"},
    {"xmlid": "journal_car", "code": "CAR", "name": "ใบสำคัญล้างลูกหนี้เงินยืม", "type": "general", "sequence": 60, "account": None},
    {"xmlid": "journal_ar", "code": "AR", "name": "ใบสำคัญลูกหนี้", "type": "sale", "sequence": 70, "account": "4000000000"},
    {"xmlid": "journal_ap", "code": "AP", "name": "ใบสำคัญซื้อ", "type": "purchase", "sequence": 80, "account": "5000000000"},
]

# Account codes other modules reference. The chart loader assigns real accounts a
# company-prefixed external id (``account_kmitl.1_a_<code>``); we publish a stable,
# company-independent ``account_kmitl.account_<code>`` for each so downstream data
# files can use ``ref`` instead of brittle search-by-code. Keep in sync with the
# codes used in the data files listed below.
REFERENCED_ACCOUNTS = [
    # account_asset_kmitl asset profiles (data/account_asset_profile.xml)
    "1251000001", "1251000003", "1251100001", "1251100003", "1251200001", "1251200003",
    "1251300001", "1251300003", "1251400001", "1251400003", "1251500001", "1251500003",
    "1251700001", "1251700003", "1252000001", "1252000003", "1253000001", "1253000003",
    "1254000001", "1254000003", "1255000001", "1255000003", "1256000001", "1256000003",
    "1257000001", "1257000003", "1258000001", "1258000003", "1259000001", "1259000003",
    "5105010004", "5105010005", "5105010006", "5105010007", "5105010008", "5105010009",
    "5105010010", "5105010011", "5105010012", "5105010013", "5105010014", "5105010015",
    "5105010016", "5105010017", "5105010019",
    # kmitl_demo partners (data/res.partner.xml)
    "1126000001", "2110000001", "2110000099",
]


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
        account = get_account(data["account"]) if data["account"] else Account.browse()
        if not journal:
            vals = {
                "name": data["name"],
                "code": data["code"],
                "type": data["type"],
                "company_id": company.id,
                "sequence": data["sequence"],
            }
            if account:
                vals["default_account_id"] = account.id
            journal = Journal.create(vals)
        elif account and not journal.default_account_id:
            # Backfill a default account added after the journal was created.
            journal.default_account_id = account.id
        env["ir.model.data"]._update_xmlids(
            [
                {
                    "xml_id": "account_kmitl.%s" % data["xmlid"],
                    "record": journal,
                    "noupdate": True,
                }
            ]
        )

    # Point each bank journal's payment method lines at its own default account.
    bank_codes = [j["code"] for j in JOURNALS if j["type"] == "bank"]
    bank_journals = Journal.search(
        [
            ("company_id", "=", company.id),
            ("code", "in", bank_codes),
        ]
    )
    for journal in bank_journals:
        if journal.default_account_id:
            lines = (
                journal.inbound_payment_method_line_ids
                + journal.outbound_payment_method_line_ids
            )
            lines.payment_account_id = journal.default_account_id


# KMITL payment methods (data/account_payment_method.xml). Creating a 'multi'
# method auto-adds lines only to journals existing at that moment; the KMITL
# journals are created later in this hook, so their lines are added here.
PAYMENT_METHOD_XMLIDS = [
    "account_kmitl.payment_method_transfer_out",
    "account_kmitl.payment_method_transfer_in",
    "account_kmitl.payment_method_cheque_out",
    "account_kmitl.payment_method_cheque_in",
    "account_kmitl.payment_method_cash_out",
    "account_kmitl.payment_method_cash_in",
]


def _setup_payment_method_lines(env, company):
    """Offer the KMITL payment methods (เงินโอน / เช็ค / เงินสด) on every
    KMITL bank journal, in both directions.

    Idempotent: journals already carrying a method are skipped. New and
    pre-existing lines without a payment account are pointed at the journal's
    default account, the same convention ``_create_journals`` applies to the
    stock manual lines.
    """
    Journal = env["account.journal"]
    MethodLine = env["account.payment.method.line"]
    methods = env["account.payment.method"]
    for xmlid in PAYMENT_METHOD_XMLIDS:
        method = env.ref(xmlid, raise_if_not_found=False)
        if method:
            methods |= method
    if not methods:
        return

    bank_codes = [j["code"] for j in JOURNALS if j["type"] == "bank"]
    journals = Journal.search(
        [("company_id", "=", company.id), ("code", "in", bank_codes)]
    )
    for journal in journals:
        lines = (
            journal.inbound_payment_method_line_ids
            + journal.outbound_payment_method_line_ids
        )
        for method in methods - lines.payment_method_id:
            MethodLine.create(
                {
                    "journal_id": journal.id,
                    "payment_method_id": method.id,
                    "name": method.name,
                }
            )
        if journal.default_account_id:
            lines = (
                journal.inbound_payment_method_line_ids
                + journal.outbound_payment_method_line_ids
            )
            lines.filtered(
                lambda l: not l.payment_account_id
            ).payment_account_id = journal.default_account_id


def _register_account_xmlids(env, company):
    """Publish stable, company-independent external ids for the accounts that
    other modules reference (e.g. account_asset_kmitl asset profiles,
    kmitl_demo partners).

    The chart loader assigns real accounts a company-coupled xmlid
    (``account_kmitl.1_a_<code>``). Downstream modules should not hard-code the
    company prefix, so we publish ``account_kmitl.account_<code>`` pointing at the
    same record. Idempotent: ``_update_xmlids`` upserts on (module, name), so
    re-running reuses existing rows. Missing codes are logged, never fatal.
    """
    Account = env["account.account"]

    data_list = []
    for code in REFERENCED_ACCOUNTS:
        account = Account.search(
            [("code", "=", code), ("company_id", "=", company.id)], limit=1
        )
        if not account:
            _logger.warning(
                "account_kmitl: account code %s not found for company %s; "
                "skipping external id account_kmitl.account_%s.",
                code,
                company.display_name,
                code,
            )
            continue
        data_list.append(
            {
                "xml_id": "account_kmitl.account_%s" % code,
                "record": account,
                "noupdate": True,
            }
        )
    if data_list:
        env["ir.model.data"]._update_xmlids(data_list)


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
    _setup_payment_method_lines(env, company)
    _register_account_xmlids(env, company)
    _deactivate_default_journals(env, company)
    _create_withholding_taxes(env, company)
