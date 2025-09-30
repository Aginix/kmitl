# -*- coding: utf-8 -*-
{
    'name': 'Account Asset Purchase',
    'version': '16.0.1.0.0',
    'summary': """ Account Asset Purchase Summary """,
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "KMITL",
    'depends': ['base', 'web'],
    "data": [
        "security/ir.model.access.csv",
        "views/purchase_asset_line_views.xml"
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
