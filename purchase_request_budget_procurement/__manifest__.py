# -*- coding: utf-8 -*-
{
    "name": "Purchase Request Budget Procurement",
    "version": "16.0.1.2.0",
    "category": "KMITL",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "depends": ["procurement_plan_budget", "purchase_request_budget", "product_kmitl"],
    "data": [
        "data/purchase_request_exception.xml",
        "views/purchase_request_views.xml",
        "views/procurement_plan_views.xml",
    ],
    "application": False,
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
