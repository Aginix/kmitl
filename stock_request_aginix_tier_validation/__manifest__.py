# -*- coding: utf-8 -*-
{
    'name': 'Stock Request Aginix Tier Validation',
    'version': '16.0.1.0.0',
    'summary': """ Stock Request Aginix Tier Validation Summary """,
    "category": "KMITL",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    'depends': ['stock_request_aginix', 'base_tier_validation'],
    "data": [
        "data/tier_definition.xml",
        "views/stock_request_views.xml",
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
