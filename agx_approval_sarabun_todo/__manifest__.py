{
    "name": "Aginix Approval Sarabun Todos",
    "version": "16.0.1.0.0",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "Accounting",
    "summary": "ต่อยอด agx_approval_budget_todo: เมื่อจองงบประมาณแล้วแจ้งผู้สร้างให้สร้างหนังสือ "
    "เพื่อส่งขออนุมัติ และแจ้ง FYI กลับเมื่อคำขอได้รับอนุมัติ",
    "depends": [
        "agx_approval_budget_todo",
        "agx_approval_sarabun",
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
