{
    "name": "Purchase Request KMITL Viewer",
    "version": "16.0.1.0.0",
    "summary": "Grant purchase viewer read-only access to KMITL Purchase Request models",
    "category": "KMITL",
    "author": "KMITL",
    "depends": ["purchase_request_viewer", "purchase_request_kmitl"],
    "data": [
        "security/ir.model.access.csv",
        "views/menus.xml",
    ],
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
