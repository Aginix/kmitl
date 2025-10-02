# -*- coding: utf-8 -*-
{
    'name': 'L10n th gov gpsc',
    'version': '16.0.1.0.0',
    'summary': """ L10n th gov gpsc Summary """,
    "category": "KMITL",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    'depends': ['base', 'purchase'],
    "data": [
        "security/ir.model.access.csv",
        "data/procurement.gpsc.csv",
        "views/procurement_gpsc_views.xml"
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
