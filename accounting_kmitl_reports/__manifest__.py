# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    "name": "KMITL Accounting Reports",
    "version": "16.0.2.0.0",
    "category": "KMITL/Accounting",
    "summary": "KMITL accounting reports: Trial Balance, Profit and Loss, "
    "Balance Sheet, Cash Flow Statement",
    "author": "KMITL",
    "website": "https://www.kmitl.ac.th",
    "license": "LGPL-3",
    "depends": [
        "accounting_kmitl",
        "account_fiscal_year",
        "thai_date_utils",
        # OCA building blocks (clone from OCA/account-financial-reporting 16.0)
        "mis_template_financial_report",
        "mis_builder_cash_flow",
        "account_financial_report",
        "report_xlsx",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/mis_report_style_kmitl.xml",
        "data/mis_report_pl_kmitl.xml",
        "data/mis_report_bs_kmitl.xml",
        "data/mis_report_cf_kmitl.xml",
        "data/mis_report_instance_kmitl.xml",
        "data/paperformat_trial_balance_kmitl.xml",
        "data/report_action_trial_balance_kmitl.xml",
        "report/trial_balance_kmitl_template.xml",
        "views/menuitem.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "accounting_kmitl_reports/static/src/trial_balance/multi_record_select.js",
            "accounting_kmitl_reports/static/src/trial_balance/trial_balance.js",
            "accounting_kmitl_reports/static/src/trial_balance/trial_balance.xml",
            "accounting_kmitl_reports/static/src/trial_balance/trial_balance.scss",
        ],
    },
    "installable": True,
    "auto_install": False,
}
