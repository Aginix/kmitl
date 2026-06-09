# -*- coding: utf-8 -*-
{
    'name': 'Account Asset Batch',
    'version': '16.0.1.0.0',
    'summary': """ Account Asset Batch Summary """,
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "KMITL",
    'depends': ['account_asset_number_kmitl', 'purchase_kmitl', 'l10n_th_gov_gpsc'],
    "data": [
        "security/ir.model.access.csv",
        "views/account_asset_batch_line_views.xml",
        "views/account_asset_batch_views.xml",
        "views/account_asset_views.xml",
        "views/purchase_order_views.xml",
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
