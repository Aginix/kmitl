# -*- coding: utf-8 -*-
{
    'name': 'Purchase Request Approval KMITL',
    'version': '16.0.1.0.0',
    'summary': """ Purchase Request Approval System for KMITL """,
    'author': 'Aginix Techonologies',
    'website': 'https://github.com/aginix/kmitl',
    'category': 'KMITL',
    'depends': ['purchase_request_kmitl'],
    "data": [
        "data/purchase_request_two_sequence.xml",
        "security/ir.model.access.csv",
        "views/purchase_request_approval_form_views.xml",
        "views/purchase_request_approval_form_line_views.xml",
        "views/purchase_request_approve_submitted_line_views.xml",
        "views/purchase_request_approve_submitted_views.xml",
        "views/purchase_request_views.xml"
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
