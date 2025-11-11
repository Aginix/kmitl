# -*- coding: utf-8 -*-
{
    'name': 'Stock Request Tier Validation Custom',
    'version': '16.0.1.0.0',
    'summary': """ Stock Request Tier Validation Custom Summary """,
    "category": "KMITL",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    'depends': ['stock_request_aginix', 'base_tier_validation'],
    "data": [
        "views/stock_request_views.xml"
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
