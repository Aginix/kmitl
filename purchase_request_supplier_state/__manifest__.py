# -*- coding: utf-8 -*-
{
    'name': 'Purchase request supplier state',
    'version': '16.0.1.0.0',
    'summary': """ Purchase request supplier state Summary """,
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "KMITL",
    'depends': ['purchase_request_approval_kmitl'],
    "data": [
        "views/purchase_request_views.xml",
        "views/res_config_settings_views.xml"
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
