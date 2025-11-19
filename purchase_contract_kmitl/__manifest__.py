# -*- coding: utf-8 -*-
{
    'name': 'Purchase Contract KMITL',
    'version': '16.0.1.0.0',
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "KMITL",
    'depends': ['purchase_exception', 'purchase_invoice_plan', 'purchase_budget'],
    "data": [
        "data/cron.xml",
        "data/purchase_exception.xml",
        "views/purchase_contract_type_views.xml",
        "views/purchase_order_views.xml",
        "views/purchase_contract_menu.xml",
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
