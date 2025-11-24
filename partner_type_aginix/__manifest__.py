# -*- coding: utf-8 -*-
{
    'name': 'Partner Type Aginix',
    'version': '16.0.1.0.0',
    'summary': """ Partner Type Aginix Summary """,
    'author': 'Aginix Technologies',
    'website': 'https://github.com/aginix/kmitl',
    'category': 'KMITL',
    'depends': ['account', 'purchase'],
    "data": [
        "security/ir.model.access.csv",
        "views/res_partner_type_views.xml",
        "views/res_partner_views.xml"
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
