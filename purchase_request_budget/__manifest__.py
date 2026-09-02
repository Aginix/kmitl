{
    "name": "Purchase Request Budget",
    "version": "16.0.1.6.0",
    "summary": """ Purchase Request Budget Summary """,
    "category": "KMITL",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "depends": [
        "budget",
        "budget_product",
        "purchase_request_kmitl",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/purchase_request_exception.xml",
        "views/purchase_request_views.xml",
        "views/budget_commitment_views.xml",
    ],
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
