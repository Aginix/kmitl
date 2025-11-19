# -*- coding: utf-8 -*-
{
    'name': 'Purchase Contract KMITL',
    'version': '16.0.1.0.0',
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "KMITL",
    'depends': ['purchase_exception', 'purchase_invoice_plan', 'purchase_budget'],
    "data": [
        "views/purchase_order_views.xml",
        "data/purchase_exception.xml",
        "data/cron.xml"
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
