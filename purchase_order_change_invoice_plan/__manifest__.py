# -*- coding: utf-8 -*-
{
    'name': 'Purchase Order Change Invoice Plan',
    'version': '16.0.1.0.0',
    'summary': """ Purchase Order Change Invoice Plan Summary """,
    'author': 'Aginix Technologies',
    'website': 'https://github.com/aginix/kmitl',
    'category': 'KMITL',
    'depends': ['purchase_order_change', 'purchase_invoice_plan'],
    'data': [
        "wizards/purchase_order_change_wizard_views.xml",
        "data/purchase_change_section_data.xml",
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
