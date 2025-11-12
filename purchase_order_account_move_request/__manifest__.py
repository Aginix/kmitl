# -*- coding: utf-8 -*-
{
    'name': 'Purchase Order Account Move Request',
    'version': '16.0.1.0.0',
    'summary': """ Purchase Order Account Move Request Summary """,
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "KMITL",
    'depends': ['purchase', 'account_move_request', 'purchase_order_payment_type'],
    "data": [
        "views/purchase_order_views.xml"
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
