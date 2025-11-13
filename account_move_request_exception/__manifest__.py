# -*- coding: utf-8 -*-
{
    'name': 'Account Move Request Exception',
    'version': '16.0.1.0.0',
    'summary': """ Account Move Request Exception Summary """,
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "Accounting",
    'depends': ['base_exception', 'account_move_request'],
    "data": [
        "security/ir.model.access.csv",
        "views/account_move_request_views.xml",
        "wizards/account_move_request_exception_confirm.xml"
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
