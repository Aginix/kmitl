{
    "name": "Advance Payment - Overview Report",
    "summary": "รายงานภาพรวมสัญญายืมเงิน: every loan with its BC, AR/PR, voucher and "
    "DR numbers on one screen, exportable to Excel and PDF",
    "version": "16.0.1.0.0",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "KMITL",
    "depends": [
        # ใบจองงบ (BC) column.
        "advance_payment_budget_commitment",
        # ใบเบิกชดใช้เงินยืม (DR) column; pulls in the OU and due-status fields.
        "advance_payment_disbursement",
        # MultiRecordSelect, fiscal years and Thai date formatting.
        "accounting_kmitl_reports",
        "report_xlsx",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/paperformat.xml",
        "data/report_actions.xml",
        "report/overview_report_template.xml",
        "views/menu.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "advance_payment_overview_report/static/src/overview_report/*",
        ],
    },
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
