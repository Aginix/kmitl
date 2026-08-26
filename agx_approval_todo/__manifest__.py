{
    "name": "Aginix Approval Todos",
    "version": "16.0.1.0.0",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "Accounting",
    "summary": "แจ้ง Todo ให้เจ้าหน้าที่จองงบประมาณเมื่อคำขออนุมัติเข้าสถานะ "
    "รอตรวจสอบ/จองงบประมาณ และล้าง Todo เมื่อจองแล้วหรือออกจากสถานะนั้น",
    "depends": [
        "agx_approval",
        "mail_activity_todo_role_unit",
        "budget_role",
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
