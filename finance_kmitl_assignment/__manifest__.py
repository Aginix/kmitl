# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    "name": "Finance Assignment KMITL",
    "version": "16.0.1.1.0",
    "category": "KMITL/Finance",
    "summary": "Auto-assign a responsible finance officer to payment vouchers by rules",
    "author": "KMITL",
    "website": "https://www.kmitl.ac.th",
    "license": "LGPL-3",
    "depends": [
        "finance_kmitl",
        "partner_type_aginix",
    ],
    "data": [
        "security/ir.model.access.csv",
        "wizards/assign_officer_wizard_views.xml",
        "views/account_payment_views.xml",
        "views/assignment_rule_views.xml",
        "views/finance_assignment_menus.xml",
    ],
    "installable": True,
    "auto_install": False,
}
