# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name": "KMITL Product Data",
    "version": "16.0.0.0.0",
    "category": "KMITL",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "depends": [
        "stock",
        "account_kmitl",
        "product_category_code_unique",
    ],
    "data": [               
        "data/product_category.xml",
        "data/product_template_storable.xml",
        "data/product_template_consumable.xml",
        "data/product_template_asset.xml",
    ],
    "application": False,
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
