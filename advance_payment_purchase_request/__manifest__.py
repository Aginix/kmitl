{
    "name": "Advance Payment - Purchase Request",
    "summary": "Create loan contracts from purchase requests",
    "version": "16.0.1.0.0",
    "category": "Accounting",
    "author": "KMITL",
    "license": "LGPL-3",
    "depends": [
        "advance_payment",
        "purchase_request_kmitl",
        "purchase_request_department",
        "purchase_request_budget",
    ],
    "data": [
        "views/purchase_request_views.xml",
    ],
    "installable": True,
    "auto_install": False,
}
