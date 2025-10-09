# -*- coding: utf-8 -*-
{
    "name": "Purchase Approval KMITL",
    "version": "",
    "author": "",
    "website": "",
    "category": "",
    "depends": ["purchase_request_kmitl", "purchase_no_rfq", "purchase_tier_validation"],
    "data": [
        "data/sequence.xml",
        "security/ir.model.access.csv",
        "views/purchase_order_views.xml",
        "views/purchase_request_report_views.xml",
        "views/purchase_request_views.xml"
    ],
    "application": False,
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
