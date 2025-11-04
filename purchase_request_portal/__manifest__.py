# -*- coding: utf-8 -*-
{
    "name": "Purchase Request Portal",
    "version": "16.0.1.0.0",
    "summary": "Portal access for Purchase Requests with HTML report display",
    "category": "KMITL/Portal",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "depends": [
        "purchase_request",
        "purchase_request_report_kmitl",
        "portal",
    ],
    "data": [
        "views/portal_templates.xml",
    ],
    "assets": {
        'web.assets_frontend': [
            'purchase_request_portal/static/src/js/purchase_request_portal_sidebar.js',
        ],
    },
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
