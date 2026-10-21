{
    "name": "KMITL Purchase Request Approval Exception",
    "version": "16.0.1.0.0",
    "summary": """ base.exception framework for reviewing พจ.1 before ส่งเข้าสารบรรณ """,
    "category": "KMITL/Purchases",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "depends": [
        "purchase_request_approval",
        "base_exception",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/exception_rule_data.xml",
        "wizard/purchase_request_approval_exception_confirm_view.xml",
        "views/purchase_request_approval_views.xml",
    ],
    "auto_install": True,
    "application": False,
    "license": "AGPL-3",
}
