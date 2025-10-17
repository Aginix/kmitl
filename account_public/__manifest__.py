# -*- coding: utf-8 -*-
{
    'name': 'Account Public',
    'version': '16.0.1.0.0',
    'summary': """ Account Public Summary """,
    "category": "Accounting/Localizations/Account Charts",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    'depends': ['account'],
    "data": [
        "security/ir.model.access.csv",
        "views/account_analytic_account_public_views.xml"
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
