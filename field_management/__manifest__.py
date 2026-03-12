# -*- coding: utf-8 -*-
{
    'name': 'Field Management',
    'version': '16.0.1.0.0',
    'summary': """ Field Management Summary """,
    "category": "KMITL",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    'depends': ['base'],
    'data': [
        'views/readonly_management_views.xml',
        'views/invisible_management_views.xml',
        'views/required_management_views.xml',
        'security/ir.model.access.csv',
        'views/readonly_management_fields_views.xml',
        'views/invisible_management_fields_views.xml',
        'views/required_management_fields_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
