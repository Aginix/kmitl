{
    "name": "Purchase Tax Adjustment KMITL",
    "summary": "Adjust VAT amount on PR, PR approval and PO totals "
    "without changing line prices (like vendor bills)",
    "version": "16.0.1.0.0",
    "category": "KMITL",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "depends": [
        "purchase",
        "purchase_request_price_tax_included",
        "purchase_request_approval",
    ],
    "data": [
        "views/purchase_request_views.xml",
        "views/purchase_request_approval_views.xml",
        "views/purchase_order_views.xml",
    ],
    "installable": True,
    "license": "LGPL-3",
}
