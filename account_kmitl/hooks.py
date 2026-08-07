import logging

from odoo import SUPERUSER_ID, api

from .models.account_payment_method import KMITL_PAYMENT_METHODS

_logger = logging.getLogger(__name__)

# Journal master data. ``account`` is the account code used as the journal's
# default account (resolved after the chart is loaded); ``None`` when the
# journal has no default account. Bank journals also point their payment method
# lines at that same default account.
JOURNALS = [
    {
        "xmlid": "journal_jv",
        "code": "JV",
        "name": "ใบสำคัญทั่วไป",
        "type": "general",
        "sequence": 10,
        "account": None,
    },
    {
        "xmlid": "journal_pv",
        "code": "PV",
        "name": "ใบสำคัญจ่าย",
        "type": "bank",
        "sequence": 20,
        "account": "1112210004",
    },
    {
        "xmlid": "journal_pvr",
        "code": "PVR",
        "name": "ใบสำคัญส่งคืนลูกหนี้เงินยืม",
        "type": "bank",
        "sequence": 30,
        "account": "1112000006",
    },
    {
        "xmlid": "journal_rv",
        "code": "RV",
        "name": "ใบสำคัญรับ",
        "type": "bank",
        "sequence": 40,
        "account": "1112210004",
    },
    {
        "xmlid": "journal_par",
        "code": "PAR",
        "name": "ใบสำคัญจ่ายลูกหนี้เงินยืม",
        "type": "bank",
        "sequence": 50,
        "account": "1112110004",
    },
    {
        "xmlid": "journal_car",
        "code": "CAR",
        "name": "ใบสำคัญล้างลูกหนี้เงินยืม",
        "type": "general",
        "sequence": 60,
        "account": None,
    },
    {
        "xmlid": "journal_ar",
        "code": "AR",
        "name": "ใบสำคัญลูกหนี้",
        "type": "sale",
        "sequence": 70,
        "account": "4000000000",
    },
    {
        "xmlid": "journal_ap",
        "code": "AP",
        "name": "ใบสำคัญซื้อ",
        "type": "purchase",
        "sequence": 80,
        "account": "5000000000",
    },
]

# The institute's paying accounts (หัวจ่าย) as given by the treasury office: the
# bank account money leaves from, the chart code of the GL account it is booked
# against, and the way it normally leaves. A current account can be both
# transferred from and drawn cheques on, so a second method for the same account
# is added by hand when it is needed rather than assumed here.
#
# The branch each account is held at is noted in the comments only. Odoo keeps a
# branch on ``res.bank`` (one record per branch, carrying the code the bank files
# ask for), not on the account, so naming it here would be data nothing reads.
#
# The account numbers are restated here rather than read out of the chart, even
# though the chart's account *names* happen to carry them
# (``ธ.ไทยพาณิชย์ /ย่อยเทคโนฯ /SA-088-2-11066-5``). Those names are not written to
# one shape — some separate with ``บ/ช``, some glue a note onto the number, some
# put a space inside the ``CA-`` prefix — and none carry a BIC, so a parser would
# need this table anyway and would fail silently into a wrong account number in a
# file sent to a bank. Stated, it fails loudly.
#
# ``acc_number`` empty means cash: there is no bank account, only a GL account.
#
# They all hang off ใบสำคัญจ่าย (PV): a paying account is a payment method line,
# and a method line belongs to a journal.
PAYING_ACCOUNTS = [
    # ธ.ไทยพาณิชย์ /ย่อยเทคโนฯ
    {
        "account": "1112210004",
        "method": "kmitl_transfer",
        "bic": "SICOTHBK",
        "acc_number": "088-2-11066-5",
    },
    # ธ.ไทยพาณิชย์ /ย่อยเทคโนฯ — the account KMITL's cheques are drawn on
    {
        "account": "1112220015",
        "method": "kmitl_cheque",
        "bic": "SICOTHBK",
        "acc_number": "088-3-00303-1",
    },
    # ธ.ไทยพาณิชย์ /เทคโนฯ
    {
        "account": "1112110012",
        "method": "kmitl_transfer",
        "bic": "SICOTHBK",
        "acc_number": "088-2-60881-2",
    },
    # ธ.ไทยพาณิชย์ /ย่อยเทคโนฯ
    {
        "account": "1112120003",
        "method": "kmitl_transfer",
        "bic": "SICOTHBK",
        "acc_number": "088-3-00005-9",
    },
    # ธ.กรุงไทย /หัวตะเข้
    {
        "account": "1112120002",
        "method": "kmitl_transfer",
        "bic": "KRTHTHBK",
        "acc_number": "028-6-01583-8",
    },
    # ธ.กรุงศรีอยุธยา /ย่อยเทคโนฯ
    {
        "account": "1112120016",
        "method": "kmitl_transfer",
        "bic": "AYUDTHBK",
        "acc_number": "507-0-00013-4",
    },
    # ธ.กสิกรไทย /ลาดกระบัง
    {
        "account": "1112120006",
        "method": "kmitl_transfer",
        "bic": "KASITHBK",
        "acc_number": "036-1-00165-6",
    },
    # เงินสด — booked against the institute's cash-on-hand account, not a bank
    # account. Without this entry the cash method line keeps the GL account
    # _setup_payment_method_lines hands every line (the journal's own bank
    # account), so paying cash would credit a bank.
    {
        "account": "1111000002",
        "method": "kmitl_cash",
        "bic": False,
        "acc_number": False,
    },
]

# The voucher (ใบสำคัญ) the paying accounts belong to.
PAYING_ACCOUNT_JOURNAL_CODE = "PV"

# Account codes other modules reference. The chart loader assigns real accounts a
# company-prefixed external id (``account_kmitl.1_a_<code>``); we publish a stable,
# company-independent ``account_kmitl.account_<code>`` for each so downstream data
# files can use ``ref`` instead of brittle search-by-code. Keep in sync with the
# codes used in the data files listed below.
REFERENCED_ACCOUNTS = [
    # account_asset_kmitl asset profiles (data/account_asset_profile.xml)
    "1251000001",
    "1251000003",
    "1251100001",
    "1251100003",
    "1251200001",
    "1251200003",
    "1251300001",
    "1251300003",
    "1251400001",
    "1251400003",
    "1251500001",
    "1251500003",
    "1251700001",
    "1251700003",
    "1252000001",
    "1252000003",
    "1253000001",
    "1253000003",
    "1254000001",
    "1254000003",
    "1255000001",
    "1255000003",
    "1256000001",
    "1256000003",
    "1257000001",
    "1257000003",
    "1258000001",
    "1258000003",
    "1259000001",
    "1259000003",
    "5105010004",
    "5105010005",
    "5105010006",
    "5105010007",
    "5105010008",
    "5105010009",
    "5105010010",
    "5105010011",
    "5105010012",
    "5105010013",
    "5105010014",
    "5105010015",
    "5105010016",
    "5105010017",
    "5105010019",
    # kmitl_demo partners (data/res.partner.xml)
    "1126000001",
    "2110000001",
    "2110000099",
]


def _drop_dedicated_payment_sequence(journal):
    """Number a payment PV/… rather than PPV/….

    Core keeps a *dedicated payment sequence* on bank and cash journals so that
    payments do not share a running number with the invoices in the same journal:
    ``account.move._get_starting_sequence`` prefixes a "P" onto the journal code
    for payment moves whenever ``payment_sequence`` is set, and the compute turns
    it on for every bank/cash journal.

    A KMITL journal code *is* the voucher type (ใบสำคัญ) and its sequence *is* the
    voucher number, so ใบสำคัญจ่าย has to number PV/2026/08/0001. There is nothing
    to keep the payments apart from either — a voucher journal carries payments
    and nothing else.

    Guarded on the field's presence: it belongs to core, not to us, and a rename
    there should leave the numbering wrong rather than break the install.
    """
    if "payment_sequence" not in journal._fields:
        _logger.warning(
            "account_kmitl: account.journal has no payment_sequence field; "
            "payments on %s may be numbered P%s/… instead of %s/….",
            journal.display_name,
            journal.code,
            journal.code,
        )
        return
    if journal.payment_sequence:
        journal.payment_sequence = False


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
        _drop_dedicated_payment_sequence(journal)
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


# Odoo's built-in methods, offered on every stock bank journal. KMITL pays
# only by transfer / cheque / cash, so these are taken off its journals.
STOCK_METHOD_XMLIDS = [
    "account.account_payment_method_manual_in",
    "account.account_payment_method_manual_out",
]


def _kmitl_payment_journals(env, company):
    """Every journal that can carry a payment method line for the company.

    Archived journals are included: ``_deactivate_default_journals`` archives
    the journals the chart loader created, and un-archiving one later must not
    bring Odoo's Manual method back into service.
    """
    return (
        env["account.journal"]
        .with_context(active_test=False)
        .search([("company_id", "=", company.id), ("type", "in", ("bank", "cash"))])
    )


def _setup_payment_method_lines(env, company):
    """Offer the KMITL payment methods (เงินโอน / เช็ค / เงินสด) on every
    bank/cash journal, in both directions, and drop Odoo's stock Manual one.

    ``account.journal._default_*_payment_methods`` (overridden in
    ``models/account_journal.py``) already gives every journal created from now
    on the KMITL methods; this pass fixes up the journals that already exist —
    the ones created before this module was installed, and the KMITL journals
    ``_create_journals`` creates a few lines above.

    Idempotent: methods already on a journal are left alone. Lines without a
    payment account are pointed at the journal's default account, the same
    convention ``_create_journals`` applies. Removing a Manual line that a
    payment already uses only detaches it from the journal (core
    ``account.payment.method.line.unlink``), so posted history is preserved.
    """
    MethodLine = env["account.payment.method.line"]
    stock_methods = env["account.payment.method"]
    for xmlid in STOCK_METHOD_XMLIDS:
        method = env.ref(xmlid, raise_if_not_found=False)
        if method:
            stock_methods |= method

    sequences = {method["code"]: method["sequence"] for method in KMITL_PAYMENT_METHODS}
    for journal in _kmitl_payment_journals(env, company):
        wanted = env["account.payment.method"]
        for payment_type in ("inbound", "outbound"):
            wanted |= journal._kmitl_default_payment_methods(payment_type)
        if not wanted:
            continue
        lines = (
            journal.inbound_payment_method_line_ids
            + journal.outbound_payment_method_line_ids
        )
        for method in wanted - lines.payment_method_id:
            MethodLine.create(
                {
                    "journal_id": journal.id,
                    "payment_method_id": method.id,
                    "name": method.name,
                    "sequence": sequences.get(method.code, 10),
                }
            )
        lines = (
            journal.inbound_payment_method_line_ids
            + journal.outbound_payment_method_line_ids
        )
        if journal.default_account_id:
            lines.filtered(
                lambda line: not line.payment_account_id
            ).payment_account_id = journal.default_account_id
        lines.filtered(lambda line: line.payment_method_id in stock_methods).unlink()


def _seed_bank_accounts(env, company):
    """Create the institute's own bank accounts, the ones money is paid out of.

    Returned keyed by the chart code of the GL account each is booked against,
    which is how ``_setup_paying_account_lines`` looks them up again.

    Idempotent and best-effort: an existing account with the same (sanitized)
    number is reused, and a BIC that no ``res.bank`` carries leaves the bank
    empty with a warning rather than failing the install — the account number is
    what the file needs, the bank only names it.
    """
    from odoo.addons.base.models.res_bank import sanitize_account_number

    Bank = env["res.bank"]
    PartnerBank = env["res.partner.bank"]
    accounts = {}
    unknown_bics = []
    for entry in PAYING_ACCOUNTS:
        if not entry["acc_number"]:
            continue  # cash: no bank account to seed
        bank = Bank.search([("bic", "=", entry["bic"])], limit=1)
        if not bank:
            unknown_bics.append("%s (%s)" % (entry["bic"], entry["acc_number"]))
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
        elif not bank_account.bank_id and bank:
            bank_account.bank_id = bank.id
        accounts[entry["account"]] = bank_account

    if unknown_bics:
        _logger.warning(
            "account_kmitl: no res.bank found for BIC %s; the paying accounts "
            "on them carry no bank, so the e-payment file's sending bank code "
            "will be blank. Create the banks and re-run the setup.",
            "; ".join(unknown_bics),
        )
    return accounts


def _setup_paying_account_lines(env, company):
    """Give ใบสำคัญจ่าย one outbound payment method line per paying account.

    A paying account (หัวจ่าย) is "out of which bank account the money leaves, by
    which means, booked against which GL account" — which is what a payment
    method line already says, so it needs no model of its own. This turns the
    generic lines ``_setup_payment_method_lines`` puts on the journal into the
    treasury office's actual list: one line per account, named after it, booked
    against it.

    Only the outbound side of PV is reshaped. Its inbound lines are left alone
    because PV is the lowest-sequence bank journal and therefore the journal every
    payment falls back to, receipts included; the other journals are left alone
    too.

    Each line is also given the institute's own bank account, which is what the
    e-payment file sends as its sending account and what a payee's bank is
    auto-matched against. เงินสด has none — it books against the cash-on-hand
    account and never reaches a bank.

    Idempotent: a line already booked against the right account is reused as it
    is, and a generic line of the same method is repointed rather than duplicated.
    Each create runs in its own savepoint so that a chart missing one account, or
    a core constraint refusing a second line of the same method on one journal,
    is reported instead of aborting the install.
    """
    Account = env["account.account"]
    MethodLine = env["account.payment.method.line"]
    bank_accounts = _seed_bank_accounts(env, company)
    journal = env["account.journal"].search(
        [
            ("code", "=", PAYING_ACCOUNT_JOURNAL_CODE),
            ("company_id", "=", company.id),
        ],
        limit=1,
    )
    if not journal:
        _logger.warning(
            "account_kmitl: journal %s not found for %s; paying accounts must "
            "be set up by hand.",
            PAYING_ACCOUNT_JOURNAL_CODE,
            company.display_name,
        )
        return

    existing = journal.outbound_payment_method_line_ids
    claimed = MethodLine.browse()
    failed = []
    for sequence, entry in enumerate(PAYING_ACCOUNTS, start=1):
        gl_account = Account.search(
            [("code", "=", entry["account"]), ("company_id", "=", company.id)],
            limit=1,
        )
        method = env.ref(
            "account_kmitl.payment_method_%s_out"
            % entry["method"].removeprefix("kmitl_"),
            raise_if_not_found=False,
        )
        if not gl_account or not method:
            failed.append("%s (%s)" % (entry["account"], entry["method"]))
            continue
        bank_account = bank_accounts.get(entry["account"])
        name = "%s – %s" % (method.name, gl_account.name)
        vals = {
            "name": name,
            "payment_account_id": gl_account.id,
            "bank_account_id": bank_account.id if bank_account else False,
            "sequence": sequence * 10,
        }
        # Already the right account: leave it exactly as configured.
        line = (existing - claimed).filtered(
            lambda row: (
                row.payment_method_id == method and row.payment_account_id == gl_account
            )
        )[:1]
        if not line:
            # A generic line of the same method — repoint it instead of adding a
            # duplicate alongside it.
            line = (existing - claimed).filtered(
                lambda row: row.payment_method_id == method
            )[:1]
        try:
            with env.cr.savepoint():
                if line:
                    line.write(vals)
                else:
                    line = MethodLine.create(
                        dict(vals, journal_id=journal.id, payment_method_id=method.id)
                    )
        except Exception as error:  # noqa: BLE001 - never abort the install
            failed.append("%s (%s: %s)" % (entry["account"], entry["method"], error))
            continue
        # Publish a stable external id per paying account so data files can
        # ``ref`` one — they are made here rather than in XML (the journal does
        # not exist until the chart is loaded), and a payment subject has to
        # name one.
        env["ir.model.data"]._update_xmlids(
            [
                {
                    "xml_id": "account_kmitl.paying_account_%s" % entry["account"],
                    "record": line,
                    "noupdate": True,
                }
            ]
        )
        claimed |= line

    if claimed:
        _logger.info(
            "account_kmitl: %d paying account(s) (หัวจ่าย) set up on %s.",
            len(claimed),
            journal.display_name,
        )
    if failed:
        _logger.warning(
            "account_kmitl: could not set up paying account(s) on %s: %s — "
            "add them by hand in the journal's Outgoing Payments.",
            journal.display_name,
            "; ".join(failed),
        )


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
    _setup_paying_account_lines(env, company)
    _register_account_xmlids(env, company)
    _deactivate_default_journals(env, company)
    _create_withholding_taxes(env, company)
