# -*- coding: utf-8 -*-
{
    'name': 'Purchase Request Budget',
    'version': '16.0.1.0.0',
    'summary': """ Purchase Request Budget Summary """,
    "category": "KMITL",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    'depends': ['purchase_request_kmitl', 'budget'],
    "data": [
        "security/purchase_request.xml",
        "views/purchase_request_views.xml"
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
