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
        "report/paperformat.xml",
        "report/receipt_summary_pdf_template.xml",
        "report/receipt_summary_pdf_action.xml",
        "views/receipt_remittance_views.xml",
        "views/menus.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "receipt_kmitl_summary_report/static/src/receipt_summary/receipt_summary.js",
            "receipt_kmitl_summary_report/static/src/receipt_summary/receipt_summary.xml",
        ],
    },
    "installable": True,
    "application": False,
}
