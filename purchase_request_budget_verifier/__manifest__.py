{
    "name": "Purchase Request Budget Verifier",
    "version": "16.0.1.1.0",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "KMITL",
    "summary": "ผู้ยืนยันงบประมาณ พ.1: ระบุผู้จองงบประมาณรายใบ และส่ง Todo ให้เมื่อรอจองงบประมาณ",
    "depends": [
        "purchase_request_budget_todo",
        "purchase_request_verifier",
    ],
    "data": [
        "data/purchase_request_exception.xml",
        "views/purchase_request_views.xml",
    ],
    "post_init_hook": "post_init_hook",
    "uninstall_hook": "uninstall_hook",
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
