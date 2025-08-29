# -*- coding: utf-8 -*-
{
    "name": "Procurement Plan Analytic",
    "version": "16.0.1.0.0",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "KMITL",
    'depends': ['account_analytic_kmitl', 'procurement_plan'],
    'data': [
        "data/account.analytic.plan.csv",
        'views/analytic_views.xml',
        "views/procurement_plan_views.xml"
    ],
    'application': False,
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
