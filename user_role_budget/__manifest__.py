# -*- coding: utf-8 -*-
{
    'name': 'User Role Budget',
    'version': '16.0.1.0.0',
    'summary': """ User Role Budget Summary """,
    "category": "KMITL",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    'depends': ['budget', 'base_user_role', 'disbursement', 'procurement_plan', 'agx_sarabun', 'operating_unit_access_all'],
    'data': [
        'data/res.users.role.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
