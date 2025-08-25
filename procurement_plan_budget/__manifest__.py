# -*- coding: utf-8 -*-
{
    "name": "Procurement Plan Budget",
    "version": "16.0.1.0.0",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "KMITL",
    'depends': ['procurement_plan', 'procurement_plan_analytic', 'budget', 'web'],
    "data": [
        "views/budget_appropriation_views.xml",
        "views/procurement_plan_views.xml"
    ],
    'application': False,
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
