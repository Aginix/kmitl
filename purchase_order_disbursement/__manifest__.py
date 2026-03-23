# -*- coding: utf-8 -*-
{
    'name': 'Purchase Order Disbursement',
    'version': '16.0.1.0.0',
    'summary': """ Purchase Order Disbursement Summary """,
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "KMITL",
    'depends': ['purchase', 'disbursement', 'purchase_order_payment_type', 'account_payment_kmitl'],
    "data": [
        "security/ir.model.access.csv",
        "views/disbursement_request_views.xml",
        "views/purchase_order_views.xml"
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
