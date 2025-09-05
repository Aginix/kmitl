# -*- coding: utf-8 -*-
{
    'name': 'Purchase Request KMITL',
    'version': '16.0.1.0.0',
    'summary': """ Purchase Request KMITL""",
    "category": "KMITL",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    'depends': ['l10n_th_gov_purchase_request'],
    "data": [
        "data/purchase_request_exception.xml",
        "data/purchase_request_rules.xml",
        "views/purchase_request_views.xml",
        "wizards/purchase_request_line_make_purchase_order_views.xml",
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
