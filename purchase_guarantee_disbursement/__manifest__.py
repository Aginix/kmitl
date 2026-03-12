{
    "name": "Purchase Guarantee Disbursement",
    "version": "16.0.1.0.0",
    "summary": "Create disbursement requests to refund purchase guarantees",
    "author": "KMITL",
    "website": "https://www.kmitl.ac.th",
    "category": "KMITL",
    "depends": ["purchase_guarantee_kmitl", "disbursement"],
    "data": [
        "security/ir.model.access.csv",
        "views/disbursement_request_views.xml",
        "views/purchase_guarantee_views.xml",
    ],
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
