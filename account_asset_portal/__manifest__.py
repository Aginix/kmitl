# -*- coding: utf-8 -*-
{
    'name': 'Account Asset Portal',
    'version': '16.0.1.0.0',
    'summary': """ Account Asset Portal Summary """,
    "category": "KMITL",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    'depends': ['portal', 'l10n_th_gov_account_asset_management', 'account_asset_number_kmitl'],
    "data": [
        "views/account_asset_views.xml",
        "views/templates.xml"
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
