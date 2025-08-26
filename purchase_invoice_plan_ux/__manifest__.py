# -*- coding: utf-8 -*-
{
    'name': 'Purchase Invoice Plan UX',
    'version': '16.0.1.0.0',
    'summary': """ Purchase Invoice Plan UX """,
    'author': 'Aginix Techonologies',
    'website': 'https://github.com/aginix/kmitl',
    'category': 'KMITL',
    'depends': ['purchase_invoice_plan', 'purchase_order_kmitl'],
    'data': [
        "views/purchase_create_invoice_plan_views.xml",
        "views/purchase_invoice_inherit_views.xml",
        "views/purchase_invoice_plan_views.xml",
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
