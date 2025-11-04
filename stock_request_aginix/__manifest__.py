# -*- coding: utf-8 -*-
{
    'name': 'Stock Request Aginix',
    'version': '16.0.1.0.0',
    'summary': """ Stock Request Aginix Summary """,
    "category": "KMITL",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    'depends': ['stock'],
    "data": [
        "security/ir.model.access.csv",
        "views/menu.xml",
        "views/stock_picking_views.xml",
        "views/stock_request_views.xml"
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
