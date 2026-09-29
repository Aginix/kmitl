{
    "name": "Purchase Request Approval Sarabun",
    "version": "16.0.1.0.0",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "KMITL",
    "depends": [
        "purchase_request_approval",
        "purchase_request_sarabun",
        "agx_sarabun_layout",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/sarabun_route_template_data.xml",
        "wizards/purchase_request_approval_return_cancel_wizard_views.xml",
        "views/purchase_request_approval_views.xml",
        "report/report_purchase_request_approval_sarabun.xml",
    ],
    "installable": True,
    "auto_install": True,
    "license": "LGPL-3",
}
