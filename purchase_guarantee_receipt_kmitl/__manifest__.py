{
    "name": "Purchase Guarantee Receipt KMITL",
    "version": "16.0.1.0.0",
    "summary": "Issue a guarantee receipt from a purchase guarantee",
    "category": "Accounting/Accounting",
    "author": "KMITL",
    "website": "https://www.kmitl.ac.th",
    "depends": [
        "purchase_guarantee_kmitl",
        "receipt_kmitl",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/product_data.xml",
        "views/receipt_kmitl_views.xml",
        "views/purchase_guarantee_views.xml",
    ],
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
