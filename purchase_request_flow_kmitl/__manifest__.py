{
    "name": "Purchase Request Flow (KMITL)",
    "summary": "One cascade for ดึงกลับ / ตีกลับ / ยกเลิก across พ.1, หนังสือ, "
    "ใบจองเงิน, e-GP and พจ.1",
    "version": "16.0.1.0.0",
    "category": "KMITL",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "depends": [
        "purchase_request_approval",
        "purchase_request_budget",
        "purchase_request_egp",
    ],
    "data": [
        "security/ir.model.access.csv",
        "wizards/purchase_request_flow_wizard_views.xml",
        "views/purchase_request_views.xml",
        "views/purchase_request_approval_views.xml",
        "views/res_config_settings_views.xml",
    ],
    "installable": True,
    "license": "LGPL-3",
}
