# -*- coding: utf-8 -*-
{
    'name': 'Purchase Request Approval KMITL Budget',
    'version': '16.0.1.0.0',
    'summary': """ Purchase Request Approval KMITL Budget Summary """,
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "KMITL",
    'depends': ['purchase_request_approval_kmitl', 'purchase_request_budget', 'purchase_request_security'],
    "data": [
        "views/purchase_request_views.xml"
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
