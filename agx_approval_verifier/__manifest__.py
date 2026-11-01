{
    "name": "Aginix Approval Designated Verifier",
    "version": "16.0.1.1.0",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "Accounting",
    "summary": "ผู้ขอระบุผู้ตรวจสอบคำขอ (ผู้ตรวจสอบ) ก่อนส่งตรวจสอบ "
    "และแจ้ง Todo ให้ผู้ตรวจสอบเมื่อคำขอเข้าสถานะรอตรวจสอบข้อมูล",
    "depends": [
        "agx_approval",
        "mail_activity_todo",
    ],
    "data": [
        "data/mail_activity_type.xml",
        "views/approval_request_views.xml",
    ],
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
