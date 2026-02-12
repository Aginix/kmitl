# -*- coding: utf-8 -*-
{
    'name': 'Account Asset Menu',
    'version': '16.0.1.0.0',
    'summary': """ Account Asset Menu Summary """,
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "KMITL",
    'depends': ['account_asset_purchase', 'account_asset_usability_kmitl'],
    "data": [
        "data/sequence.xml",
        "views/account_asset_batch_views.xml"
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
