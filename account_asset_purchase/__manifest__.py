# -*- coding: utf-8 -*-
{
    'name': 'Account Asset Purchase',
    'version': '16.0.1.0.0',
    'summary': """ Account Asset Purchase Summary """,
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "KMITL",
    'depends': ['account_asset_number_kmitl', 'purchase'],
    "data": [
        "security/ir.model.access.csv",
        "views/account_asset_bartch_views.xml",
        "views/account_asset_batch_views.xml",
        "views/purchase_asset_batch_line​_views.xml",
        "views/purchase_asset_batch_line_views.xml",
        "views/purchase_asset_line_views.xml",
        "views/purchase_order_views.xml"
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
