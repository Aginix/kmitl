# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    "name": "Disbursement ↔ KMITL Finance Bridge",
    "version": "16.0.1.0.0",
    "category": "KMITL/Finance",
    "summary": "DR ↔ Payment: enable payment creation from disbursement "
    "requests, WHT calc, deferred reconciliation, and pipeline status sync",
    "author": "KMITL",
    "website": "https://www.kmitl.ac.th",
    "license": "LGPL-3",
    "depends": [
        "disbursement",
        "finance_kmitl",
        "disbursement_accounting_kmitl",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/disbursement_request_views.xml",
    ],
    "installable": True,
    "auto_install": False,
}
