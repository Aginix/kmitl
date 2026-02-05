# -*- coding: utf-8 -*-
{
    'name': 'Account Asset Subcomponent Kmitl',
    'version': '16.0.1.0.0',
    'summary': """ Account Asset Subcomponent Kmitl Summary """,
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "KMITL",
    'depends': ['account_asset_number_kmitl'],
    'data': [
        "security/ir.model.access.csv",
        "views/account_asset_views.xml",
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
