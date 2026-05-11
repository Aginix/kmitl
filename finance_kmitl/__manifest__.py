# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    "name": "KMITL Finance",
    "version": "16.0.1.1.0",
    "category": "KMITL/Finance",
    "summary": "งานการเงิน KMITL: จ่ายเงิน, bank export, WHT, รายรับ/ใบเสร็จ",
    "license": "LGPL-3",
    "author": "KMITL",
    "website": "https://www.kmitl.ac.th",
    "depends": [
        "account",
        "accounting_kmitl",
        "account_fiscal_year_enhance",
        "budget",
        "l10n_th_bank_payment_export",
        "l10n_th_bank_payment_export_format",
        "thai_date_utils",
        "l10n_th_fonts",
        "l10n_th_amount_to_text",
        "l10n_th_account_wht_cert_form"
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/kmitl_payment_type_data.xml",
        "data/tier_definition.xml",
        "views/kmitl_payment_type_views.xml",
        "views/account_payment_views.xml",
        "views/bank_payment_export_views.xml",
        "views/menuitem.xml",
        "report/paperformat.xml",
        "report/report_bank_payment_export_action.xml",
        "report/report_bank_payment_export.xml",
    ],
    "installable": True,
    "application": True,
}
