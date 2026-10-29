{
    "name": "Aginix Approval Disbursement Operating Unit",
    "version": "16.0.1.0.0",
    "summary": "ผู้ที่อ่านใบขอเบิกได้ อ่านใบขออนุมัติที่ใบขอเบิกอ้างอิงได้ด้วย",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "KMITL",
    "depends": [
        "agx_approval_operating_unit",
        "agx_approval_disbursement",
    ],
    "data": ["security/security.xml"],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "auto_install": True,
    "license": "LGPL-3",
}
