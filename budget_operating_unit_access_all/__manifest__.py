# -*- coding: utf-8 -*-
{
    'name': 'Budget Operating Unit Access All',
    'version': '16.0.1.3.0',
    'summary': """ Budget Operating Unit Access All""",
    'author': 'Aginix Technologies',
    'website': 'https://github.com/Aginix/kmitl',
    'category': 'KMITL/Budgeting',
    'depends': ['budget_operating_unit', 'operating_unit_access_all'],
    'data': [
        "security/budget_security.xml",
        "views/budget_transfer_views.xml",
        "views/budget_commitment_views.xml",
    ],
    'installable': True,
    'license': 'LGPL-3',
}
