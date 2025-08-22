# -*- coding: utf-8 -*-
{
    'name': 'Purchase Request Approval Exception Kmitl',
    'version': '16.0.1.0.0',
    'summary': """ Purchase Request Approval Exception Kmitl Summary """,
    'author': 'Aginix Techonologies',
    'website': 'https://github.com/aginix/kmitl',
    'category': 'KMITL',
    'depends': ['purchase_request_approval_kmitl', 'base_exception'],
    "data": [
        "data/purchase_request_approval_data.xml",
        "security/ir.model.access.csv",
        "views/purchase_request_approval_form_views.xml",
        "wizards/purchase_request_approval_form_exception_confirm.xml"
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
