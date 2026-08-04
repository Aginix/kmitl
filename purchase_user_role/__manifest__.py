# -*- coding: utf-8 -*-
{
    'name': 'Purchase User Role',
    'version': '16.0.1.0.0',
    'summary': """ Purchase User Role Summary """,
    "category": "KMITL",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    'depends': ['budget', 'base_user_role', 'agx_sarabun', 'operating_unit_access_all', 'purchase_request_kmitl', 'account', 'purchase_manual_delivery_security'],
    'data': [
        "data/res_users_role.xml",
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
