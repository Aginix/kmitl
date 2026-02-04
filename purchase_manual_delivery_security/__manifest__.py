# -*- coding: utf-8 -*-
{
    'name': 'Purchase Manual Delivery Security',
    'version': '16.0.1.0.0',
    'summary': """ Purchase Manual Delivery Security Summary """,
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "Purchase",
    'depends': ['purchase_manual_delivery'],
    "data": [
        "security/security.xml",
        "views/purchase_order_views.xml",
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
