# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    "name": "Disbursement Assignment KMITL",
    "version": "16.0.1.0.1",
    "category": "Disbursement",
    "summary": "Auto-assign a responsible officer to disbursement requests at "
    "each station by rules",
    "author": "KMITL",
    "website": "https://www.kmitl.ac.th",
    "license": "LGPL-3",
    "depends": [
        "disbursement",
        "disbursement_wc",
    ],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "wizards/assign_officer_wizard_views.xml",
        "views/disbursement_request_views.xml",
        "views/assignment_rule_views.xml",
        "views/disbursement_verification_menus.xml",
    ],
    "installable": True,
    "auto_install": False,
}
