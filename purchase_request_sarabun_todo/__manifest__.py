{
    "name": "Purchase Request Sarabun Todos",
    "version": "16.0.1.0.0",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "Purchases",
    "summary": "แจ้งเจ้าของ พ.1 ผ่าน Todo inbox เมื่อสารบรรณส่งผลลัพธ์กลับ "
    "(อนุมัติ/ตีกลับ/ปฏิเสธ)",
    "depends": [
        "purchase_request_sarabun",
        "mail_activity_todo",
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
