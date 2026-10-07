{
    "name": "Aginix Approval Designated Verifier",
    "version": "16.0.1.0.0",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "Accounting",
    "summary": "ผู้ขอระบุผู้ตรวจสอบคำขอ (ผู้ตรวจสอบที่ระบุ) ก่อนส่งตรวจสอบ "
    "และแจ้ง Todo ให้ผู้ตรวจสอบที่ระบุเมื่อคำขอเข้าสถานะรอตรวจสอบข้อมูล",
    "depends": [
        "agx_approval",
        "mail_activity_todo",
        "base_automation",
    ],
    "data": [
        "views/approval_request_views.xml",
        "data/mail_activity_type.xml",
        "data/base_automation.xml",
    ],
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
