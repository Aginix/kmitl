# -*- coding: utf-8 -*-
{
    'name': 'Purchase Order Change',
    'version': '16.0.1.0.0',
    'summary': """ Purchase Order Change Summary """,
    'author': 'Aginix Technologies',
    'website': 'https://github.com/aginix/kmitl',
    'category': 'KMITL',
    'depends': ['purchase', 'purchase_contract_kmitl'],
    "data": [
        "security/ir.model.access.csv",
        "data/purchase_order_change.xml",
        "data/purchase_change_section_data.xml",
        "views/purchase_change_section_views.xml",
        "views/purchase_order_change_field_views.xml",
        "views/purchase_order_change_views.xml",
        "views/purchase_order_views.xml"
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
