# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    "name": "Disbursement PDF",
    "summary": "Print the standalone disbursement request (ใบขอเบิกเงิน) PDF",
    "version": "16.0.1.1.0",
    "category": "Disbursement",
    "license": "LGPL-3",
    "author": "KMITL",
    "website": "https://www.kmitl.ac.th",
    "depends": [
        "disbursement",
        "l10n_th_amount_to_text",
        "l10n_th_fonts",
    ],
    "data": [
        "report/paperformat.xml",
        "report/report_disbursement_request_action.xml",
        "report/report_disbursement_request.xml",
    ],
    "installable": True,
    "auto_install": False,
}
