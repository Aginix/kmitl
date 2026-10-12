{
    "name": "Purchase Request Approval Operating Unit",
    "version": "16.0.1.0.1",
    "summary": """ Purchase Request Approval Operating Unit Summary """,
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "KMITL",
    "depends": [
        "purchase_request_approval",
        "purchase_request_operating_unit",
        "operating_unit",
    ],
    "data": [
        "security/purchase_request_approval_operating_unit.xml",
        "views/purchase_request_approval_views.xml",
    ],
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
