# -*- coding: utf-8 -*-
{
    'name': 'User Role Purchase',
    'version': '16.0.1.0.0',
    'summary': """ User Role Purchase Summary """,
    "category": "KMITL",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    'depends': ['base_user_role', 'purchase_request_kmitl', 'budget', 'disbursement', 'procurement_plan', 'agx_sarabun', 'operating_unit_access_all'],
    'data': [
        'data/res.users.role.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
