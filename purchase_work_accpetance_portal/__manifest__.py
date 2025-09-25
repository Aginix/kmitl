# -*- coding: utf-8 -*-
{
    'name': 'Purchase Work Accpetance Portal',
    'version': '16.0.1.0.0',
    'summary': """ Purchase Work Accpetance Portal Summary """,
    "category": "KMITL",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    'depends': ['l10n_th_gov_work_acceptance', 'purchase_order_kmitl', 'portal'],
    "data": [
        "views/templates.xml",
        "views/work_acceptance_views.xml"
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
