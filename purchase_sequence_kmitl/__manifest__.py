# -*- coding: utf-8 -*-
{
    'name': 'Purchase Sequence KMITL',
    'version': '16.0.1.1.0',
    'summary': """ Purchase Sequence KMITL Summary """,
    "category": "KMITL",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    'depends': [
        'purchase_order_kmitl',
        'l10n_th_base_sequence',
    ],
    'data': [
        'data/sequence.xml',
        'views/purchase_order_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
