# -*- coding: utf-8 -*-
{
    'name': 'Purchase Order Expire',
    'version': '16.0.1.0.0',
    'summary': """ Purchase Order Expire Summary """,
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "Purchase",
    'depends': ['purchase_menu', 'purchase_contract_kmitl'],
    "data": [
        "data/ir_cron_data.xml",
        "views/purchase_order_views.xml",
        "views/action.xml",
        "views/menu.xml",
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
