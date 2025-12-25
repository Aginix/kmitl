# -*- coding: utf-8 -*-
{
    'name': 'Readonly Management',
    'version': '16.0.1.0.0',
    'summary': """ Readonly Management Summary """,
    "category": "KMITL",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    'depends': ['base', 'purchase'],
    'data': [
        'views/readonly_management_views.xml',
        'security/ir.model.access.csv'
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
