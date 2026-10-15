# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Receipt KMITL Product Data",
    "version": "16.0.1.0.0",
    "category": "KMITL/Accounting",
    "license": "AGPL-3",
    "author": "KMITL",
    "website": "https://github.com/aginix/kmitl",
    "summary": "Revenue products seeded from the KMITL chart of accounts",
    "depends": [
        "receipt_kmitl",
        "account_kmitl",
    ],
    "data": [
        "data/product_category.xml",
        "data/product_template_revenue.xml",
    ],
    "installable": True,
    "auto_install": False,
}
