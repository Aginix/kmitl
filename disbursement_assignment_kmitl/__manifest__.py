# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    "name": "Disbursement Assignment KMITL",
    "version": "16.0.1.1.0",
    "summary": "Auto-assign a responsible verification officer to disbursement "
    "requests by rules",
    "category": "Disbursement",
    "license": "LGPL-3",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "depends": [
        "disbursement",
    ],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "wizards/assign_officer_wizard_views.xml",
        "views/assignment_rule_views.xml",
        "views/disbursement_request_views.xml",
        "views/disbursement_verification_menus.xml",
    ],
    "installable": True,
    "auto_install": False,
}
