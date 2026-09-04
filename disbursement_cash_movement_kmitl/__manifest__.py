# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    "name": "Disbursement — Cash Movement",
    "version": "16.0.1.0.0",
    "category": "KMITL/Accounting",
    "summary": "Book the inter-account cash movement a disbursement voucher's "
    "money travels through, from source account to paying account",
    "author": "KMITL",
    "website": "https://www.kmitl.ac.th",
    "license": "LGPL-3",
    "depends": [
        "account_analytic_kmitl",
        "account_kmitl",
        "disbursement_finance_kmitl",
        "accounting_kmitl",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/account_move_exception_data.xml",
        "views/cash_route_views.xml",
        "views/disbursement_request_views.xml",
        "views/menuitem.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "auto_install": False,
}
