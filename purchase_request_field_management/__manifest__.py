# -*- coding: utf-8 -*-
{
    "name": "Purchase Request Field Management",
    "version": "16.0.1.0.0",
    "summary": "Field Management for Purchase Request",
    "category": "KMITL",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "depends": [
        "field_management",
        "purchase_request_kmitl",
        "purchase_request_department",
        "purchase_request_egp",
        "purchase_request_vendor_kmitl",
        "purchase_request_price_tax_included",
        "purchase_request_budget",
    ],
    "data": [
        "data/readonly_management_data.xml",
    ],
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
