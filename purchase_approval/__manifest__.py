# -*- coding: utf-8 -*-
{
    "name": "Purchase Approval KMITL",
    'version': '16.0.1.0.0',
    "category": "KMITL",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "depends": ["purchase_request_kmitl", "purchase_no_rfq"],
    "data": [
        "data/sequence.xml",
        "security/ir.model.access.csv",
        "views/purchase_request_report_views.xml",
        "views/purchase_request_views.xml"
    ],
    "application": False,
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
