# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    "name": "Disbursement Cheque",
    "summary": "Pay a disbursement request payee by cheque instead of bank transfer",
    "version": "16.0.1.0.0",
    "category": "Disbursement",
    "license": "LGPL-3",
    "author": "KMITL",
    "website": "https://www.kmitl.ac.th",
    "depends": [
        "disbursement",
        # Both ใบขอเบิก bodies print the payment method (disbursement_sarabun
        # depends on disbursement_pdf).
        "disbursement_sarabun",
    ],
    "data": [
        "views/disbursement_request_views.xml",
        "report/report_disbursement_request.xml",
    ],
    "installable": True,
    "auto_install": False,
}
