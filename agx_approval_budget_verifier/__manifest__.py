{
    "name": "Aginix Approval Designated Budget Confirmer",
    "version": "16.0.1.0.0",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "Accounting",
    "summary": "ผู้ขอ/ผู้ตรวจสอบระบุผู้ยืนยันงบประมาณรายคำขอ "
    "และแจ้ง Todo ให้เมื่อคำขอเข้าสถานะรอยืนยันงบประมาณ",
    "depends": [
        "agx_approval_budget_todo",
        "agx_approval_verifier",
    ],
    "data": [
        "views/approval_request_views.xml",
    ],
    "post_init_hook": "post_init_hook",
    "uninstall_hook": "uninstall_hook",
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
