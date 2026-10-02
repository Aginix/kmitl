{
    "name": "Purchase Request Viewer",
    "version": "16.0.1.0.0",
    "summary": "Grant purchase viewer read-only access to all purchase requests",
    "category": "KMITL",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "depends": [
        "purchase_viewer",
        "purchase_request_kmitl",
    ],
    "data": [
        "security/purchase_request_security.xml",
        "security/ir.model.access.csv",
    ],
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
