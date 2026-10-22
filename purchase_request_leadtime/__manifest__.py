# -*- coding: utf-8 -*-
{
    'name': 'Purchase Request Leadtime',
    'version': '16.0.1.0.0',
    'summary': """ Purchase Request Leadtime Summary """,
    "category": "KMITL",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    'depends': ['base_state_leadtime', 'purchase_request_kmitl'],
    'data': [
        'views/purchase_request_view.xml',
    ],
    'application': False,
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
