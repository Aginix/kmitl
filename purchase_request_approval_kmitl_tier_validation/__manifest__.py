# -*- coding: utf-8 -*-
{
    'name': 'Purchase Request Approval KMITL Tier Validation',
    'version': '16.0.1.0.0',
    'summary': """ Purchase Request Approval KMITL Tier Validation Summary """,
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "KMITL",
    'depends': ['purchase_request_tier_validation', 'purchase_request_approval_kmitl'],
    "data": [
        "views/purchase_request_views.xml"
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
