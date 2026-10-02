{
    "name": "Purchase Invoice Plan Viewer",
    "version": "16.0.1.0.0",
    "summary": "Grant purchase viewer read-only access to Purchase Invoice Plans",
    "category": "KMITL",
    "author": "KMITL",
    "depends": ["purchase_viewer", "purchase_invoice_plan"],
    "data": [
        "security/ir.model.access.csv",
    ],
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
