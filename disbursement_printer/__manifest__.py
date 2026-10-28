# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    "name": "Disbursement Printer",
    "summary": "Print the disbursement request's หนังสือ (Sarabun layout), "
    "granted to selected users",
    "version": "16.0.1.0.0",
    "category": "Disbursement",
    "license": "LGPL-3",
    "author": "KMITL",
    "website": "https://www.kmitl.ac.th",
    "depends": [
        "disbursement_sarabun",
    ],
    "data": [
        "security/security.xml",
        "views/disbursement_request_views.xml",
    ],
    "installable": True,
    "auto_install": False,
}
