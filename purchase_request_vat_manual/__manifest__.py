{
    "name": "Purchase Request VAT Manual",
    "version": "16.0.1.0.0",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "KMITL",
    "summary": "Allow editing the computed VAT amount on purchase requests",
    "depends": ["purchase_request_price_tax_included"],
    "data": [
        "security/ir.model.access.csv",
        "wizard/purchase_request_vat_wizard_views.xml",
        "views/purchase_request_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "purchase_request_vat_manual/static/src/components/**/*",
        ],
    },
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
