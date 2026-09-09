# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Receipt KMITL",
    "version": "16.0.1.1.0",
    "category": "KMITL/Accounting",
    "license": "AGPL-3",
    "author": "KMITL",
    "summary": "Cash receipting and central posting workflow for KMITL",
    "depends": [
        "account",
        "mail",
        "account_analytic_kmitl",
        "l10n_th_amount_to_text",
    ],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/partner_walkin_data.xml",
        "data/mail_activity_data.xml",
        "wizard/receipt_remittance_reject_view.xml",
        "views/payment_method_views.xml",
        "views/receipt_kmitl_views.xml",
        "views/receipt_remittance_views.xml",
        "views/res_partner_views.xml",
        "views/walkin_partner_action.xml",
        "views/res_config_settings_views.xml",
        "views/receipt_report_action.xml",
        "views/menus.xml",
        "report/paperformat.xml",
        "report/receipt_kmitl_report.xml",
        "report/receipt_kmitl_action.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "receipt_kmitl/static/src/components/*.js",
            "receipt_kmitl/static/src/components/*.xml",
            "receipt_kmitl/static/src/views/*.js",
            "receipt_kmitl/static/src/views/*.xml",
        ],
    },
    "installable": True,
    "application": True,
}
