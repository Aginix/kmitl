# -*- coding: utf-8 -*-
{
    'name': 'Purchase Work Acceptance Invoice Plan Account Move Request',
    'version': '16.0.1.0.0',
    'summary': """ Purchase Work Acceptance Invoice Plan Account Move Request Summary """,
    "category": "KMITL",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    'depends': ['purchase_work_acceptance_invoice_plan', 'purchase_work_acceptance_invoice_plan_usability', 'purchase_order_account_move_request'],
    "data": [
        "views/purchase_invoice_plan_views.xml",
        "views/purchase_order_views.xml"
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
