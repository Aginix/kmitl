# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    "name": "Payment",
    "version": "16.0.1.1.0",
    "category": "Accounting",
    "summary": "ระบบเบิกจ่ายเงิน - รวมการสร้างรายการจ่าย และส่งข้อมูล e-Payment",
    "license": "LGPL-3",
    "author": "KMITL",
    "website": "https://www.kmitl.ac.th",
    "depends": [
        "account",
        "account_move_kmitl",
        "account_fiscal_year_enhance",
        "l10n_th_bank_payment_export",
        "l10n_th_bank_payment_export_format",
        "thai_date_utils",
        "l10n_th_fonts",
        "l10n_th_amount_to_text",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/kmitl_payment_type_data.xml",
        "views/kmitl_payment_type_views.xml",
        "views/account_payment_views.xml",
        "views/bank_payment_export_views.xml",
        "report/paperformat.xml",
        "report/report_bank_payment_export_action.xml",
        "report/report_bank_payment_export.xml",
    ],
    "installable": True,
    "application": True,
}
