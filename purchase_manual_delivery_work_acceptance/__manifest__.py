# -*- coding: utf-8 -*-
{
    'name': 'Purchase Manual Delivery Work Acceptance',
    'version': '16.0.1.0.0',
    'summary': """ Purchase Manual Delivery Work Acceptance Summary """,
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "KMITL",
    'depends': ['purchase_manual_delivery', 'purchase_work_acceptance_invoice_plan_usability'],
    "data": [
        "views/purchase_order_views.xml",
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
