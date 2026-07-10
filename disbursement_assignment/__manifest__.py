# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    "name": "Disbursement Assignment",
    "version": "16.0.1.0.0",
    "summary": "Assign verification officers to disbursement requests via "
    "rules and manual actions",
    "category": "Disbursement",
    "license": "LGPL-3",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "depends": [
        "base_assignment",
        "disbursement",
    ],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "wizards/return_request_wizard_views.xml",
        "views/disbursement_request_assignment_views.xml",
        "views/assignment_rule_views.xml",
        "views/disbursement_verification_menus.xml",
    ],
    "installable": True,
    "auto_install": False,
}
