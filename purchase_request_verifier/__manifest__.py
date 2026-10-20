{
    "name": "Purchase Request Verifier",
    "version": "16.0.1.0.0",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "KMITL",
    "summary": "ผู้ยืนยันตรวจสอบ พ.1: ระบุผู้ตรวจสอบรายใบ และส่ง Todo ให้เมื่อส่งคำขอ",
    "depends": [
        "mail_activity_todo",
        "purchase_request_kmitl",
    ],
    "data": [
        "data/mail_activity_type.xml",
        "views/purchase_request_views.xml",
    ],
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
