{
    "name": "Aginix Approval Disbursement Todos",
    "version": "16.0.2.0.0",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "Accounting",
    "summary": "ต่อยอด agx_approval_budget_todo สายการเบิกจ่าย: แจ้ง FYI ผู้ขอเมื่อ"
    "ใบขอเบิกของคำขอตัดงบแล้ว และเมื่อปิดคำขอ",
    "depends": [
        "agx_approval_budget_todo",
        "agx_approval_disbursement",
        "base_automation",
    ],
    "data": [
        "data/mail_activity_type.xml",
        "data/base_automation.xml",
    ],
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
