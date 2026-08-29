# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Receipt KMITL Summary Report",
    "version": "16.0.1.0.0",
    "category": "KMITL/Accounting",
    "license": "AGPL-3",
    "author": "KMITL",
    "summary": "Receipt Summary Report for Receipt KMITL",
    "depends": [
        "receipt_kmitl",
        "accounting_kmitl_reports",
        "report_xlsx",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/receipt_summary_xlsx_action.xml",
        "views/menus.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "receipt_kmitl_summary_report/static/src/receipt_summary/receipt_summary.js",
            "receipt_kmitl_summary_report/static/src/receipt_summary/receipt_summary.xml",
            "receipt_kmitl_summary_report/static/src/receipt_summary/receipt_summary.scss",
        ],
    },
    "installable": True,
    "application": False,
}
