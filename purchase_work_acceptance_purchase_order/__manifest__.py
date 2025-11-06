# -*- coding: utf-8 -*-
{
    'name': 'Purchase Work Acceptance Purchase Order',
    'version': '16.0.1.0.0',
    'summary': """ Purchase Work Acceptance Purchase Order Summary """,
    "category": "KMITL",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    'depends': ['l10n_th_gov_work_acceptance'],
    "data": [
        "views/purchase_order_views.xml",
        "views/work_acceptance_views.xml"
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
