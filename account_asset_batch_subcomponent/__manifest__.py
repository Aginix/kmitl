# -*- coding: utf-8 -*-
{
    'name': 'Account Asset Batch Subcomponent',
    'version': '16.0.1.0.0',
    'summary': """ Account Asset Batch Subcomponent Summary """,
    "category": "KMITL",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    'depends': ['account_asset_batch', 'account_asset_subcomponent_kmitl'],
    "data": [
        "security/ir.model.access.csv",
        "views/account_asset_batch_subcomponent_views.xml",
        "views/account_asset_batch_views.xml",
        "wizards/batch_subcomponent_wizard.xml"
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
