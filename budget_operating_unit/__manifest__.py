# -*- coding: utf-8 -*-
{
    'name': 'Budget Operating Unit',
    'version': '16.0.1.2.0',
    'summary': """ Budget Operating Unit """,
    'author': 'Aginix Technologies',
    'website': 'https://github.com/Aginix/kmitl',
    'category': 'KMITL/Budgeting',
    'depends': ['operating_unit', 'budget', 'budget_transfer'],
    "data": [
        "security/budget_security.xml",
        "views/budget_commitment_views.xml",
        "views/budget_move_views.xml",
        "views/budget_transfer_views.xml",
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
