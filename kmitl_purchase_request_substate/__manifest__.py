# -*- coding: utf-8 -*-
{
    'name': 'Kmitl Purchase Request Substate',
    'version': '16.0.1.0.0',
    'summary': """ Kmitl Purchase Request Substate """,
    "category": "KMITL",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    'depends': ['purchase_request_substate'],
    "data": [
        "security/purchase_request_substate.xml",
        "views/purchase_request_views.xml"
    ],
    'application': True,
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
