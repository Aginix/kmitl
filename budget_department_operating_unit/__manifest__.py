# -*- coding: utf-8 -*-
{
    'name': 'Budget Department Operating Unit',
    "version": "16.0.1.0.0",
    "category": "KMITL/Budgeting",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "depends": ["budget_department", "budget_operating_unit", "hr_department_operating_unit"],
    "data": [
        "views/budget_commitment_views.xml",
        "views/budget_move_views.xml",
        "views/budget_transfer_views.xml"
    ],
    'application': False,
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
