# -*- coding: utf-8 -*-
{
    'name': 'Purchase Approval Tier Validaiton',
    'version': '16.0.1.0.0',
    'summary': """ Purchase Approval Tier Validaiton Summary """,
    "category": "KMITL",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    'depends': ['purchase_approval', 'base_tier_validation'],
    "data": [
        "views/purchase_request_report_views.xml"
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
