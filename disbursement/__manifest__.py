# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    "name": "Disbursement",
    "version": "16.0.1.0.0",
    "category": "Disbursement",
    "license": "LGPL-3",
    "author": "KMITL",
    "depends": [
        "account",
        "budget",
        "account_fiscal_year_enhance",
        "finance_kmitl",
        "base_exception",
        "l10n_th_account_tax",
        "base_fontawesome",
        "partner_type_aginix",
    ],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/sequence.xml",
        "wizards/disbursement_exception_confirm.xml",
        "views/disbursement_request_views.xml",
        "views/budget_commitment_views.xml",
        "views/exception_rule_views.xml",
        "report/paperformat.xml",
        "report/report_disbursement_request_action.xml",
        "report/report_disbursement_request.xml",
        "views/portal_templates.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "disbursement/static/src/js/disbursement_sidebar.js",
        ],
    },
    "installable": True,
    "application": True,
}
