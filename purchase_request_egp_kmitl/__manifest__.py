# -*- coding: utf-8 -*-
{
    'name': 'Purchase Request e-GP Status',
    'version': '16.0.1.0.0',
    'summary': """ Purchase Request e-GP Status """,
    "category": "KMITL",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    'depends': ['purchase_request_egp', 'purchase_request_security', 'purchase_request_kmitl_tier_validation'],
    "data": [
        "data/tier_validation_exception.xml",
        "views/purchase_request_views.xml"
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
