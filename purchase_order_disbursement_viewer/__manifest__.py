{
    "name": "Purchase Order Disbursement Viewer",
    "version": "16.0.1.0.0",
    "summary": "Grant purchase viewer read-only access to disbursement requests",
    "category": "KMITL",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "depends": [
        "purchase_order_disbursement",
        "purchase_viewer",
    ],
    "data": [
        "security/ir.model.access.csv",
    ],
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
