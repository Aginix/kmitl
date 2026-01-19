# -*- coding: utf-8 -*-
{
    "name": "Purchase Request Sarabun Integration",
    "summary": "Integrate Purchase Request with Sarabun document routing",
    "version": "16.0.1.0.0",
    "category": "Purchases",
    "author": "KMITL",
    "website": "https://www.kmitl.ac.th",
    "license": "LGPL-3",
    "depends": [
        "purchase_request",
        "agx_sarabun",
    ],
    "data": [
        "views/purchase_request_views.xml",
        "data/sarabun_route_template_data.xml",
    ],
    "installable": True,
    "auto_install": False,
}
