{
    "name": "Aginix Approval Disbursement Todos",
    "version": "16.0.1.0.0",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "Accounting",
    "summary": "ต่อยอด agx_approval_todo สายการเงิน/เบิกจ่าย: บันทึกค่าใช้จ่ายจริง, "
    "แจ้งการเงินตรวจสอบและตั้งเบิก, และ FYI เมื่อเบิกจ่ายแล้ว",
    "depends": [
        "agx_approval_todo",
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
