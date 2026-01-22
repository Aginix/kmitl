# -*- coding: utf-8 -*-
{
    'name': 'Purchase Order Change Committee',
    'version': '16.0.1.0.0',
    'summary': """ Purchase Order Change Committee Summary """,
    'author': 'Aginix Technologies',
    'website': 'https://github.com/aginix/kmitl',
    'category': 'KMITL',
    'depends': ['purchase_order_change'],
    "data": [
        "data/purchase_change_section_data.xml",
        "wizards/purchase_order_change_wizard.xml"
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
