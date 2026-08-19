# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "KMITL Accounting Workflow",
    "version": "16.0.1.2.0",
    "category": "KMITL/Accounting",
    "summary": "Workflow อนุมัติ 2 ขั้น (ผู้จัดทำ/ตรวจสอบ → ผู้อนุมัติ) "
    "บน account.move และใบสำคัญรายการบัญชี",
    "author": "KMITL",
    "website": "https://www.kmitl.ac.th",
    "license": "AGPL-3",
    "depends": [
        "accounting_kmitl",
        "mail_activity_todo",
        "l10n_th_fonts",
        "l10n_th_amount_to_text",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/mail_activity_type.xml",
        "wizards/reject_reason_views.xml",
        "views/account_move_views.xml",
        "views/account_move_queue_views.xml",
        "report/paperformat.xml",
        "report/account_move_voucher_report.xml",
        "report/account_move_voucher_templates.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "accounting_kmitl_workflow/static/src/approval_queue/multi_record_select.js",
            "accounting_kmitl_workflow/static/src/approval_queue/approval_queue.js",
            "accounting_kmitl_workflow/static/src/approval_queue/approval_queue.xml",
            "accounting_kmitl_workflow/static/src/approval_queue/approval_queue.scss",
        ],
    },
    "installable": True,
    "auto_install": False,
    "application": False,
}
