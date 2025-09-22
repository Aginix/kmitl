# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

{
    # Module Information
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
    
    # Author and Contact Information
    "author": "KMITL",
    "website": "https://www.kmitl.ac.th",
    "maintainer": "KMITL Development Team",
    
    # Legal Information
    "license": "AGPL-3",
    
    # Dependencies
    "depends": [
        "product",                        # Base Odoo product management
        "product_category_code_unique",   # Provides unique code functionality for categories
    ],
    
    # Data Files
    "data": [
        "data/product.category.csv",      # Thai government equipment classification master data
    ],
    
    # Demo Data (none for production module)
    "demo": [],
    
    # Technical Settings
    "installable": True,                  # Module can be installed
    "auto_install": False,                # Manual installation required
    "application": False,                 # Not a standalone application
    "development_status": "Beta",         # Maturity level
    
    # Version Information
    # 16.0.1.0.0 = Odoo 16.0, Module version 1.0.0
}