# -*- coding: utf-8 -*-
{
    'name': 'Purchase Request Approval Sarabun',
    'version': '16.0.1.0.0',
    'summary': 'Purchase Request Approval Sarabun Integration',
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "KMITL",
    'depends': [
        'purchase_request_approval',
        'agx_sarabun',
    ],
    "data": [
        "data/sarabun_route_template_data.xml",
        "views/purchase_request_approval_views.xml",
        "views/sarabun_document_views.xml",
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
