# -*- coding: utf-8 -*-
{
    'name': 'Purchase Order Change Committee',
    'version': '16.0.1.0.0',
    'summary': """ Purchase Order Change Committee Summary """,
    'author': 'Aginix Technologies',
    'website': 'https://github.com/aginix/kmitl',
    'category': 'KMITL',
    'depends': ['purchase_order_change', 'purchase_order_procurement_committee'],
    "data": [
        "data/purchase_change_section_data.xml",
        "views/purchase_order_change_wizard_views.xml",
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
