# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    "name": "KRIS - Research Income Sharing",
    "version": "16.0.1.0.0",
    "category": "Accounting",
    "license": "LGPL-3",
    "author": "KMITL",
    "depends": [
        "account",
        "account_fiscal_year_enhance",
        "account_analytic_kmitl",
        "mail",
    ],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/kris_sequence.xml",
        "views/kris_allocation_config_views.xml",
        "views/kris_project_views.xml",
        "views/kris_funding_receipt_views.xml",
        "views/kris_menus.xml",
    ],
    "installable": True,
    "application": True,
}
