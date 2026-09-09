# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "KMITL Finance Reports",
    "version": "16.0.2.0.0",
    "category": "KMITL/Finance",
    "summary": "รายงานของกองคลังทั้งสองทาง: รายงานการจ่ายเงิน, "
    "รายงานเจ้าหนี้ถึงกำหนดชำระ, รายงานการรับเงิน, รายงานการตั้งลูกหนี้ "
    "และรายงานลูกหนี้ถึงกำหนดชำระ",
    "author": "KMITL",
    "website": "https://www.kmitl.ac.th",
    "license": "AGPL-3",
    "depends": [
        "finance_kmitl",
        # For the ใบขอเบิก column on the payables reports: the payment's link
        # comes from here and the bill's from disbursement_accounting_kmitl,
        # which this drags in. No cycle — disbursement_finance_kmitl already
        # depends on finance_kmitl.
        "disbursement_finance_kmitl",
        # kmitl.receipt, its remittance and its payment method — the source of
        # the receipt report. finance_kmitl does not depend on this itself.
        "receipt_kmitl",
        # The dimension-filter mixin and the OWL MultiRecordSelect the filter
        # bars are built from.
        "accounting_kmitl_reports",
        "report_xlsx",
    ],
    "data": [
        "security/ir.model.access.csv",
        "security/receipt_access.xml",
        "data/paperformat.xml",
        "data/report_action_payment.xml",
        "data/report_action_payable_due.xml",
        "data/report_action_receipt.xml",
        "data/report_action_receivable_raised.xml",
        "data/report_action_receivable_due.xml",
        "report/payment_report_template.xml",
        "report/payable_due_report_template.xml",
        "report/receipt_report_template.xml",
        "report/receivable_raised_report_template.xml",
        "report/receivable_due_report_template.xml",
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
            "finance_kmitl_reports/static/src/receipt_report/receipt_report.js",
            "finance_kmitl_reports/static/src/receipt_report/receipt_report.xml",
            "finance_kmitl_reports/static/src/receipt_report/receipt_report.scss",
            "finance_kmitl_reports/static/src/receivable_raised_report/receivable_raised_report.js",
            "finance_kmitl_reports/static/src/receivable_raised_report/receivable_raised_report.xml",
            "finance_kmitl_reports/static/src/receivable_raised_report/receivable_raised_report.scss",
            "finance_kmitl_reports/static/src/receivable_due_report/receivable_due_report.js",
            "finance_kmitl_reports/static/src/receivable_due_report/receivable_due_report.xml",
            "finance_kmitl_reports/static/src/receivable_due_report/receivable_due_report.scss",
        ],
    },
    "installable": True,
    "application": False,
}
