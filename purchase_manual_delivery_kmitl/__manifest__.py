# -*- coding: utf-8 -*-
{
    'name': 'Purchase Manual Delivery Kmitl',
    'version': '16.0.1.0.0',
    'summary': """ Purchase Manual Delivery Kmitl Summary """,
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "KMITL",
    'depends': ['purchase_manual_delivery', 'purchase_kmitl'],
    "data": [
        "data/settings.xml",
        "views/purchase_order_views.xml",
        "views/stock_picking_views.xml",
        "wizards/create_manual_stock_picking.xml"
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
