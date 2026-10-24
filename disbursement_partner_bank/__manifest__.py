# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    "name": "Disbursement Payee Bank Accounts",
    "summary": "Manage a payee's bank accounts (add / edit inline) from a draft "
    "disbursement request",
    "version": "16.0.1.0.0",
    "category": "Disbursement",
    "license": "LGPL-3",
    "author": "KMITL",
    "depends": ["disbursement"],
    "data": [
        "security/ir.model.access.csv",
        "wizards/disbursement_partner_bank_wizard_views.xml",
        "views/disbursement_request_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "disbursement_partner_bank/static/src/js/list_renderer.esm.js",
            "disbursement_partner_bank/static/src/xml/list_renderer.xml",
        ],
    },
    "installable": True,
    "auto_install": False,
}
