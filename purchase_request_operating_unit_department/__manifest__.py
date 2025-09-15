# -*- coding: utf-8 -*-
{
    'name': 'Purchase Request Operating Unit Department',
    'version': '16.0.1.0.0',
    'summary': """ Purchase Request Operating Unit Department Summary """,
    "category": "KMITL",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    'depends': ['purchase_request_operating_unit', 'operating_unit_base_department', 'purchase_request_department'],
    "data": [
        "views/purchase_request_views.xml"
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
