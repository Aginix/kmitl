# -*- coding: utf-8 -*-
{
    'name': 'Purchase Request Verify State',
    'version': '16.0.1.0.0',
    'summary': """ Purchase Request Verify State Summary """,
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "KMITL",
    'depends': ['purchase_request_approval_kmitl', 'purchase_request_kmitl'],
    "data": [
        "views/purchase_request_views.xml",
        "views/res_config_settings_views.xml"
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
