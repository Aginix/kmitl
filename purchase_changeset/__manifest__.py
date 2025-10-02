# -*- coding: utf-8 -*-
{
    'name': 'Purchase Changeset',
    'version': '16.0.1.0.0',
    'summary': """ Purchase Changeset Summary """,
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "KMITL",
    'depends': ['purchase_order_kmitl'],
    "data": [
        "security/ir.model.access.csv",
        "views/changeset_views.xml",
        "views/purchase_order_views.xml",
        "wizards/purchase_committee_wizard.xml"
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
