{
    "name": "Purchase Request Approval Viewer",
    "version": "16.0.1.0.0",
    "summary": "Grant purchase viewer read-only access to Purchase Approvals (พจ.1)",
    "category": "KMITL",
    "author": "KMITL",
    "depends": ["purchase_request_kmitl_viewer", "purchase_request_approval"],
    "data": [
        "security/ir.model.access.csv",
        "views/menus.xml",
    ],
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
