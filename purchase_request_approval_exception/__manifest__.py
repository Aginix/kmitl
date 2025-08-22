# -*- coding: utf-8 -*-
{
    'name': 'Purchase Request Approval Exception',
    'version': '16.0.1.0.0',
    'summary': """ Purchase Request Approval Exception Summary """,
    'author': 'Aginix Techonologies',
    'website': 'https://github.com/aginix/kmitl',
    'category': 'KMITL',
    'depends': ['purchase_request_approval', 'base_exception'],
    "data": [
        "data/purchase_request_approval_data.xml",
        "security/ir.model.access.csv",
        "views/purchase_request_approval_views.xml",
        "wizards/purchase_request_approval_exception_confirm.xml"
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
