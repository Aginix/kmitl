# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

_logger = logging.getLogger(__name__)

_DEFAULT_PAYMENT_METHODS = [
    {
        "id": "payment_method_kasikorn_sa034",
        "name": "รับโอน (ธ.กสิกรไทย/เทคโน/SA-034-3-83718-6)",
        "sequence": 10,
        "payment_type": "cash",
        "account_code": "1111000002",
        "deposit_account_code": "1110000001",
        "journal_xmlid": "account_kmitl.journal_rv",
    },
    {
        "id": "payment_method_krungthai_69293",
        "name": "รับโอน (ธ.กรุงไทย สาขาลาดกระบัง บ/ช 69293-9)",
        "sequence": 10,
        "payment_type": "cheque",
        "account_code": "1111000002",
        "deposit_account_code": "1112110001",
        "journal_xmlid": "account_kmitl.journal_rv",
    },
    {
        "id": "payment_method_kasikorn_sa631",
        "name": "รับโอน (ธ.กสิกรไทย /ย่อยเทคโนฯ /SA-631-2-01000-1)",
        "sequence": 10,
        "payment_type": "transfer",
        "account_code": "1111000002",
        "deposit_account_code": "1112110004",
        "journal_xmlid": "account_kmitl.journal_rv",
    },
]


def post_init_hook(cr, registry):
    from odoo import api, SUPERUSER_ID

    env = api.Environment(cr, SUPERUSER_ID, {})
    _seed_payment_methods(env)


def _seed_payment_methods(env):
    Account = env["account.account"]
    PaymentMethod = env["kmitl.payment.method"]
    company = env.company

    for data in _DEFAULT_PAYMENT_METHODS:
        if PaymentMethod.search(
            [("name", "=", data["name"]), ("company_id", "=", company.id)], limit=1
        ):
            continue

        account = Account.search(
            [("code", "=", data["account_code"]), ("company_id", "=", company.id)],
            limit=1,
        )
        deposit_account = Account.search(
            [
                ("code", "=", data["deposit_account_code"]),
                ("company_id", "=", company.id),
            ],
            limit=1,
        )
        journal = env.ref(data["journal_xmlid"], raise_if_not_found=False)

        if not account or not deposit_account or not journal:
            _logger.warning(
                "receipt_kmitl: skipping payment method '%s' — "
                "account %s=%s, deposit_account %s=%s, journal %s=%s",
                data["name"],
                data["account_code"],
                bool(account),
                data["deposit_account_code"],
                bool(deposit_account),
                data["journal_xmlid"],
                bool(journal),
            )
            continue

        record = PaymentMethod.create(
            {
                "name": data["name"],
                "sequence": data["sequence"],
                "payment_type": data["payment_type"],
                "account_id": account.id,
                "deposit_account_id": deposit_account.id,
                "journal_id": journal.id,
                "company_id": company.id,
            }
        )
        env["ir.model.data"]._update_xmlids(
            [
                {
                    "xml_id": "receipt_kmitl.%s" % data["id"],
                    "record": record,
                    "noupdate": True,
                }
            ]
        )
        _logger.info("receipt_kmitl: created payment method '%s'", data["name"])
