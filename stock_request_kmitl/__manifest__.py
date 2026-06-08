# -*- coding: utf-8 -*-
{
    'name': 'Stock Request KMITL',
    'version': '16.0.1.0.0',
    'summary': """ Stock Request KMITL Summary """,
    "category": "KMITL",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    'depends': ['stock_account', 'stock_kmitl'],
    "data": [
        "data/stock_request_sequence.xml",
        "security/stock_request_security.xml",
        "security/ir.model.access.csv",
        "views/stock_picking_views.xml",
        "views/stock_request_views.xml",
        "views/menu.xml",
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
