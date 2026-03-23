# -*- coding: utf-8 -*-
{
    'name': 'Purchase Order UX',
    'version': '16.0.1.0.0',
    'summary': """ Purchase Order UX Summary """,
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "KMITL",
    'depends': ['purchase_order_kmitl', 'purchase_contract_kmitl', 'purchase_invoice_plan', 'purchase_order_payment_type', 'purchase_exception', 'purchase_stock'],
    "data": [
        "views/purchase_order_views.xml"
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
