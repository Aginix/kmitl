# -*- coding: utf-8 -*-
{
    'name': 'Purchase Request Approval Account',
    'version': '16.0.1.0.0',
    'summary': """ Purchase Request Approval Account Move Request Summary """,
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "KMITL",
    'depends': ['purchase_request_approval', 'account_move_request'],
    "data": [
        "views/account_move_request_views.xml",
        "views/purchase_request_approval_views.xml"
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
