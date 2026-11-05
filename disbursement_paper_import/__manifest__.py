# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    "name": "Disbursement Paper Import",
    "summary": "Flag disbursement requests that were keyed in from paper",
    "version": "16.0.1.1.0",
    "category": "Disbursement",
    "license": "LGPL-3",
    "author": "KMITL",
    "depends": ["disbursement"],
    "data": [
        "security/security.xml",
        "views/disbursement_request_views.xml",
    ],
    "installable": True,
    "auto_install": False,
}
