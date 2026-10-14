{
    "name": "Purchase Work Acceptance Viewer",
    "version": "16.0.1.0.0",
    "summary": "Grant purchase viewer read-only access to Work Acceptance (ตรวจรับ)",
    "category": "KMITL",
    "author": "KMITL",
    "depends": ["purchase_viewer", "purchase_work_acceptance_kmitl"],
    "data": [
        "security/ir.model.access.csv",
        "views/menus.xml",
    ],
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
