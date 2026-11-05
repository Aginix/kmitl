# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    "name": "Disbursement Payee Bank Accounts — Internal Staff Lock",
    "summary": "Hide the bank-account wizard button and block edits for internal-staff payees",
    "version": "16.0.1.0.1",
    "category": "Disbursement",
    "license": "LGPL-3",
    "author": "KMITL",
    "depends": ["disbursement_partner_bank", "hr_partner_type_kmitl"],
    "data": [
        "views/disbursement_request_views.xml",
    ],
    "installable": True,
    "auto_install": False,
}
