# -*- coding: utf-8 -*-
{
    'name': 'Purchase Order Department Operating Unit ',
    'version': '16.0.1.0.0',
    'summary': """ Purchase Order Department Operating Unit  Summary """,
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "KMITL",
    'depends': ['purchase_order_department', 'purchase_operating_unit', 'hr_department_operating_unit'],
    "data": [
        "views/purchase_order_views.xml"
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
