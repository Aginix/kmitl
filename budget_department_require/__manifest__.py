# -*- coding: utf-8 -*-
{
    'name': 'Budget Department Require',
    'version': '16.0.1.0.0',
    'summary': """ Budget Department Require Summary """,
    "category": "KMITL/Budgeting",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    'depends': ['budget_department'],
    "data": [
        "views/budget_commitment_views.xml",
        "views/budget_move_views.xml",
        "views/budget_transfer_views.xml"
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
