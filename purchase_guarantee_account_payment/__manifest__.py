{
    "name": "Purchase Guarantee Account Payment",
    "version": "16.0.2.0.0",
    "summary": "DEPRECATED - old payment route for purchase guarantees, kept so "
    "existing payments stay reachable. New receipts are issued by "
    "purchase_guarantee_receipt_kmitl.",
    "category": "Accounting/Payments",
    "author": "KMITL",
    "website": "https://www.kmitl.ac.th",
    "depends": [
        "purchase_guarantee_kmitl",
        "finance_kmitl",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/account_payment_views.xml",
        "views/purchase_guarantee_views.xml",
    ],
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
