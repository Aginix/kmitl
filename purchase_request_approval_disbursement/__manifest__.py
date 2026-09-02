# -*- coding: utf-8 -*-
{
    'name': 'Purchase Request Approval Disbursement',
    'version': '16.0.1.1.1',
    'summary': """ Purchase Request Approval Disbursement Summary """,
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "KMITL",
    'depends': ['purchase_request_approval', 'disbursement'],
    "data": [
        "views/disbursement_request_views.xml",
        "views/purchase_request_approval_views.xml"
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
