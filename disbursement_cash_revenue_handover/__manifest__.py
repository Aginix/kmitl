# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    "name": "Disbursement — Cash & Revenue Handover",
    "version": "16.0.1.0.0",
    "category": "KMITL/Accounting",
    "summary": "Hand central's cash and revenue over to the spending unit when "
    "a government-budget disbursement is billed",
    "author": "KMITL",
    "website": "https://www.kmitl.ac.th",
    "license": "LGPL-3",
    "depends": [
        "account_analytic_kmitl",
        "account_kmitl",
        "disbursement_accounting_kmitl",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/account_move_exception_data.xml",
        "views/central_funding_views.xml",
        "views/account_move_views.xml",
        "views/menuitem.xml",
    ],
    "installable": True,
    "auto_install": False,
}
