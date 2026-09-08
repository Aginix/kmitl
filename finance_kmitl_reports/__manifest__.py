# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "KMITL Finance Reports",
    "version": "16.0.1.0.0",
    "category": "KMITL/Finance",
    "summary": "รายงานฝั่งรายจ่ายของกองคลัง: รายงานการจ่ายเงิน และ รายงานเจ้าหนี้ถึงกำหนดชำระ",
    "author": "KMITL",
    "website": "https://www.kmitl.ac.th",
    "license": "AGPL-3",
    "depends": [
        "finance_kmitl",
        # For the ใบขอเบิก column on both reports: the payment's link comes
        # from here and the bill's from disbursement_accounting_kmitl, which
        # this drags in. No cycle — disbursement_finance_kmitl already depends
        # on finance_kmitl.
        "disbursement_finance_kmitl",
        # The dimension-filter mixin and the OWL MultiRecordSelect the filter
        # bars are built from.
        "accounting_kmitl_reports",
        "report_xlsx",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/paperformat.xml",
        "data/report_action_payment.xml",
        "data/report_action_payable_due.xml",
        "report/payment_report_template.xml",
        "report/payable_due_report_template.xml",
        "views/menuitem.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "finance_kmitl_reports/static/src/payment_report/payment_report.js",
            "finance_kmitl_reports/static/src/payment_report/payment_report.xml",
            "finance_kmitl_reports/static/src/payment_report/payment_report.scss",
            "finance_kmitl_reports/static/src/payable_due_report/payable_due_report.js",
            "finance_kmitl_reports/static/src/payable_due_report/payable_due_report.xml",
            "finance_kmitl_reports/static/src/payable_due_report/payable_due_report.scss",
        ],
    },
    "installable": True,
    "application": False,
}
