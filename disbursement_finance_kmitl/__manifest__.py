# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    "name": "Disbursement ↔ KMITL Finance Bridge",
    "version": "16.0.2.0.0",
    "category": "KMITL/Finance",
    "summary": "DR ↔ Payment: post-bill payment-execution workflow "
    "(audit → authorize → pay → clear), WHT, e-payment result, and "
    "pipeline status sync",
    "author": "KMITL",
    "website": "https://www.kmitl.ac.th",
    "license": "LGPL-3",
    "depends": [
        "disbursement",
        "finance_kmitl",
        "disbursement_accounting_kmitl",
        "accounting_kmitl_workflow",
    ],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/mail_activity_type.xml",
        "views/disbursement_request_views.xml",
        "views/disbursement_queue_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "disbursement_finance_kmitl/static/src/payment_queue/payment_queue.js",
            "disbursement_finance_kmitl/static/src/payment_queue/payment_queue.xml",
        ],
    },
    "installable": True,
    "auto_install": False,
}
