{
    "name": "Purchase Request Approval Todos",
    "version": "16.0.1.0.0",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "KMITL",
    "summary": "แจ้ง Todo ให้ผู้เกี่ยวข้องเมื่อ พจ.1 เปลี่ยนสถานะ ผ่าน base.automation",
    "depends": [
        "purchase_request_approval",
        "mail_activity_todo_role_unit",
        "purchase_user_role",
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
