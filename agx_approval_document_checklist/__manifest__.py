{
    "name": "Aginix Approval Document Checklist",
    "summary": "รายการเอกสารแนบที่ใช้ในการเบิกจ่าย ตามประเภทคำขออนุมัติ",
    "version": "16.0.1.0.0",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "KMITL",
    "depends": ["agx_approval", "agx_approval_disbursement"],
    "data": [
        "security/ir.model.access.csv",
        "security/security.xml",
        "views/approval_category_views.xml",
        "views/approval_request_views.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
