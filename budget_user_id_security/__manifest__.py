# -*- coding: utf-8 -*-
{
    'name': 'Budget User ID Security',
    'version': '16.0.1.0.0',
    'summary': """ Budget User ID Security Summary """,
    "category": "KMITL/Budgeting",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    'depends': ['budget'],
    "data": [
        "views/budget_commitment_views.xml",
        "views/budget_move_views.xml",
        "views/budget_transfer_views.xml"
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
