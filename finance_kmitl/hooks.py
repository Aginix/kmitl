# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import logging

from odoo import SUPERUSER_ID, api

from odoo.addons.account_kmitl.hooks import _setup_paying_account_lines

from .models.kmitl_payment_subject import _paying_account_domain

_logger = logging.getLogger(__name__)

# The treasury office's เรื่องที่จ่าย, as they gave them.
#
# Each names its หัวจ่าย by the pair that *identifies* one — the chart code of the GL
# account the money is booked against, and the way it leaves — rather than by
# external id. Those ids are published by ``account_kmitl``'s own post-init hook,
# which runs only when that module is installed: a data file that ``ref``'d them
# failed to load on every database whose chart had been set up before that hook
# learned to make them, and the failure was a hard stop in the middle of installing
# an app. Looked up here instead, a หัวจ่าย nobody set up costs one warning and one
# subject — never the install.
PAYMENT_SUBJECTS = [
    {
        # บุคลากรบังคับมีบัญชี ธ.กรุงไทย → หัวจ่าย KTB ตายตัว
        "xmlid": "payment_subject_salary",
        "name": "เงินเดือน",
        "sequence": 10,
        "method": "transfer",
        "auto_match": False,
        "default": "1112120002",
        "allowed": ["1112120002"],
    },
    {
        # จ่ายจากหัวจ่ายธนาคารเดียวกับบัญชีผู้รับ ไม่ตรงตกไป SCB
        "xmlid": "payment_subject_advance_reimburse",
        "name": "เงินยืม/สำรองจ่าย",
        "sequence": 20,
        "method": "transfer",
        "auto_match": True,
        "default": "1112210004",
        "allowed": [
            "1112210004",
            "1112110012",
            "1112120003",
            "1112120002",
            "1112120016",
            "1112120006",
        ],
    },
    {
        # หัวจ่าย SCB ตายตัว (ต่างธนาคารระบบแบงก์ route เอง)
        "xmlid": "payment_subject_vendor_direct",
        "name": "จ่ายตรงคู่ค้า",
        "sequence": 30,
        "method": "transfer",
        "auto_match": False,
        "default": "1112210004",
        "allowed": ["1112210004"],
    },
    {
        # ออกเป็นเช็คสั่งจ่ายจากบัญชีกระแส SCB
        "xmlid": "payment_subject_utilities",
        "name": "ค่าน้ำค่าไฟ",
        "sequence": 40,
        "method": "cheque",
        "auto_match": False,
        "default": "1112220015",
        "allowed": ["1112220015"],
    },
    {
        # หัวจ่ายเงินสดเงินรายได้สถาบันฯ
        "xmlid": "payment_subject_cash",
        "name": "จ่ายเงินสด",
        "sequence": 50,
        "method": "cash",
        "auto_match": False,
        "default": "1111000002",
        "allowed": ["1111000002"],
    },
]


def _paying_accounts_by_code(env, method):
    """The หัวจ่าย paid by ``method``, keyed by the chart code they book against.

    Narrowed by the very domain the model puts on the field, so what may be named
    here and what may be chosen on a subject cannot come apart.
    """
    MethodLine = env["account.payment.method.line"]
    domain = _paying_account_domain(MethodLine) + [
        ("payment_method_id", "=", method.id)
    ]
    return {line.payment_account_id.code: line for line in MethodLine.search(domain)}


def _seed_payment_subjects(env):
    """Create the เรื่องที่จ่าย and publish the external ids the rest of the system
    refers to them by.

    Idempotent, and deliberately never overwrites: a subject that already exists is
    left exactly as the treasury office has it — this is master data they adjust —
    and only gains its external id if it was missing one. A subject somebody made by
    hand under the same name is adopted rather than duplicated.
    """
    Subject = env["kmitl.payment.subject"]
    made, adopted, skipped = [], [], []
    for entry in PAYMENT_SUBJECTS:
        xml_id = "finance_kmitl.%s" % entry["xmlid"]
        method = env.ref(
            "account_kmitl.payment_method_%s_out" % entry["method"],
            raise_if_not_found=False,
        )
        if not method:
            skipped.append(
                "%s (no %s payment method)" % (entry["name"], entry["method"])
            )
            continue

        subject = env.ref(xml_id, raise_if_not_found=False) or Subject.search(
            [("name", "=", entry["name"])], limit=1
        )
        if subject:
            env["ir.model.data"]._update_xmlids(
                [{"xml_id": xml_id, "record": subject, "noupdate": True}]
            )
            adopted.append(entry["name"])
            continue

        accounts = _paying_accounts_by_code(env, method)
        default = accounts.get(entry["default"])
        if not default:
            # Without its main/fallback account there is no subject to make: the
            # field is required, and guessing another account would send money out
            # of one nobody chose.
            skipped.append(
                "%s (no %s paying account on %s)"
                % (entry["name"], entry["method"], entry["default"])
            )
            continue
        allowed = [accounts[code] for code in entry["allowed"] if code in accounts]
        missing = [code for code in entry["allowed"] if code not in accounts]
        subject = Subject.create(
            {
                "name": entry["name"],
                "sequence": entry["sequence"],
                "default_payment_method_id": method.id,
                "auto_match_payee_bank": entry["auto_match"],
                "default_paying_account_id": default.id,
                "allowed_paying_account_ids": [
                    (6, 0, [line.id for line in allowed] or [default.id])
                ],
            }
        )
        env["ir.model.data"]._update_xmlids(
            [{"xml_id": xml_id, "record": subject, "noupdate": True}]
        )
        made.append(entry["name"])
        if missing:
            _logger.warning(
                "finance_kmitl: '%s' lists paying account(s) %s that the chart does "
                "not have; it was created without them.",
                entry["name"],
                ", ".join(missing),
            )

    if made:
        _logger.info("finance_kmitl: created payment subject(s): %s.", ", ".join(made))
    if adopted:
        _logger.info(
            "finance_kmitl: payment subject(s) already present, left as they are: %s.",
            ", ".join(adopted),
        )
    if skipped:
        _logger.warning(
            "finance_kmitl: could not create payment subject(s): %s — set them up in "
            "Finance ▸ Settings ▸ Payment Subjects.",
            "; ".join(skipped),
        )
    return True


def post_init_hook(cr, registry):
    """Seed the เรื่องที่จ่าย, after making sure the หัวจ่าย they name exist.

    ``account_kmitl`` creates the หัวจ่าย in its own post-init hook, so a database
    whose chart was installed before that hook existed has none of them — and there
    is nothing for a subject to point at. That setup is idempotent, so running it
    from here costs nothing where it has already been done and is what lets this
    module install at all where it has not.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    company = env.ref("base.main_company")
    _setup_paying_account_lines(env, company)
    _seed_payment_subjects(env)
