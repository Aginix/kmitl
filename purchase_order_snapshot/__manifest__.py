# -*- coding: utf-8 -*-
{
    'name': 'Purchase Order Snapshot',
    'version': '16.0.1.0.0',
    'summary': """ Purchase Order Snapshot Summary """,
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "KMITL",
    'depends': ['purchase', 'base_snapshot'],
    "data": [
        "views/purchase_order_views.xml"
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
