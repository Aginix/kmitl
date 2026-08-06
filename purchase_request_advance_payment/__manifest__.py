{
    "name": "Purchase Request - Advance Payment Bridge",
    "version": "16.0.1.0.0",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "KMITL",
    "depends": [
        "purchase_request_kmitl",
        "purchase_request_budget",
        "advance_payment",
        "advance_payment_budget",
    ],
    "data": [
        "views/purchase_request_views.xml",
        "views/advance_payment_views.xml",
    ],
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
