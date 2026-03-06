# -*- coding: utf-8 -*-
{
    'name': 'Purchase Work Acceptance External',
    'version': '16.0.1.0.0',
    'summary': """ Purchase Work Acceptance External Summary """,
    "category": "Purchase",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    'depends': ['purchase_work_acceptance_attachment', 'purchase_work_acceptance_tier_validation'],
    "data": [
        "views/work_acceptance_views.xml",
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
