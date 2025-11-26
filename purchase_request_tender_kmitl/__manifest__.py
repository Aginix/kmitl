# -*- coding: utf-8 -*-
{
    'name': 'Purchase Request Tender KMITL',
    'version': '16.0.1.0.0',
    'summary': """ Purchase Request Tender KMITL Summary """,
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "KMITL",
    'depends': ['purchase_request_security'],
    "data": [
        "security/ir.model.access.csv",
        "security/security.xml",
        "views/purchase_request_tender_views.xml",
        "views/purchase_request_views.xml"
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
