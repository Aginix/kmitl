# -*- coding: utf-8 -*-
{
    'name': 'Purchase Request Approval Work Acceptance',
    'version': '16.0.1.0.0',
    'summary': """ Purchase Request Approval Work Acceptance Summary """,
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "KMITL",
    'depends': ['purchase_work_acceptance', 'purchase_request_approval'],
    'data': [
        "views/purchase_request_approval_views.xml",
        'security/ir.model.access.csv'
    ],
    'application': False,
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
