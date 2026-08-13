# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    "name": "KMITL Finance",
    "version": "16.0.4.0.0",
    "category": "KMITL/Finance",
    "summary": "งานการเงิน KMITL: จ่ายเงิน, bank export, WHT, ทะเบียนคุมเช็ค, รายรับ/ใบเสร็จ",
    "license": "LGPL-3",
    "author": "KMITL",
    "website": "https://www.kmitl.ac.th",
    "depends": [
        "account",
        "account_kmitl",
        "accounting_kmitl",
        "accounting_kmitl_workflow",
        "account_fiscal_year_enhance",
        "budget",
        "l10n_th_bank_payment_export",
        "l10n_th_bank_payment_export_format",
        "thai_date_utils",
        "l10n_th_fonts",
        "l10n_th_amount_to_text",
        "l10n_th_account_wht_cert_form",
    ],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/mail_activity_type.xml",
        "data/kmitl_payment_type_data.xml",
        "data/cheque_register_sequence.xml",
        "views/kmitl_payment_type_views.xml",
        "views/kmitl_payment_subject_views.xml",
        "views/kmitl_paying_account_views.xml",
        "views/account_payment_views.xml",
        "views/account_payment_list_views.xml",
        "views/account_move_views.xml",
        "views/bank_payment_export_views.xml",
        "views/cheque_register_views.xml",
        "views/cheque_layout_views.xml",
        "views/account_journal_views.xml",
        "views/menuitem.xml",
        "report/paperformat.xml",
        "report/report_bank_payment_export_action.xml",
        "report/report_bank_payment_export.xml",
        "report/report_cheque_print.xml",
        "report/report_cheque_print_action.xml",
    ],
    "assets": {
        "web.assets_backend": [
            # The stylesheet and MultiRecordSelect come from
            # accounting_kmitl_workflow's approval queue, already in this bundle.
            "finance_kmitl/static/src/clearing_queue/clearing_queue.js",
            "finance_kmitl/static/src/clearing_queue/clearing_queue.xml",
        ],
    },
    # The เรื่องที่จ่าย are seeded here rather than in a data file: they name
    # หัวจ่าย that account_kmitl publishes external ids for only when *it* is
    # installed, so a ref would fail to load on any database whose chart predates
    # that. See hooks.py.
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": True,
}
