{
    "name": "Product KMITL",
    "version": "16.0.1.0.0",
    "category": "Product",
    "summary": "KMITL Product Management with Thai Government Equipment Classification",
    "description": """
Product KMITL - Thai Government Equipment Classification

This module provides KMITL-specific product management functionality with
comprehensive Thai government equipment classification system.

Features:
=========
* Thai government equipment classification master data (596 categories)
* Hierarchical product category structure with unique codes
* Full Thai language support for category names and descriptions
* Integration with product_category_code_unique for code validation
* Government compliance for procurement and reporting

The classification system covers:
- Transportation Equipment (23000000-28000000)
- Industrial Machinery (32000000-49000000)
- Tools and Hardware (51000000-58000000)
- Electrical Equipment (59000000-67000000)
- Furniture and Office Equipment (71000000-79000000)
- Consumables and Supplies (75000000-99000000)
    """,
    "author": "KMITL",
    "website": "https://www.kmitl.ac.th",
    "maintainer": "KMITL Development Team",
    "license": "AGPL-3",
    "depends": [
        "product",
        "product_category_code_unique",
        "stock",
    ],
    "data": [
        "data/product.category.csv",
        "data/product.template.csv",
    ],
    "demo": [],
    "installable": True,
    "auto_install": False,
    "application": False,
}
