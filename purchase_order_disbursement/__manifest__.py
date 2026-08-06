# -*- coding: utf-8 -*-
{
    'name': 'Purchase Order Disbursement',
    'version': '16.0.1.1.0',
    'summary': """ Purchase Order Disbursement Summary """,
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "KMITL",
    'depends': ['purchase_kmitl', 'disbursement', 'purchase_order_kmitl'],
    "data": [
        "security/ir.model.access.csv",
        "views/disbursement_request_views.xml",
        "views/purchase_order_views.xml"
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
