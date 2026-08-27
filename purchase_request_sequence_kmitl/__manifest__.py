# -*- coding: utf-8 -*-
{
    'name': 'Purchase Request Sequence KMITL',
    'version': '16.0.1.0.0',
    'summary': """ Purchase Request Sequence KMITL Summary """,
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "KMITL",
    'depends': ['purchase_request_kmitl', 'l10n_th_base_sequence'],
    'data': [
        'data/sequence.xml',
        'views/purchase_request_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
