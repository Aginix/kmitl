{
    "name": "Purchase Request Viewer",
    "version": "16.0.1.0.0",
    "summary": "Grant purchase viewer read-only access to Purchase Requests",
    "category": "KMITL",
    "author": "KMITL",
    "depends": ["purchase_viewer", "purchase_request"],
    "data": [
        "security/ir.model.access.csv",
        "views/menus.xml",
    ],
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
