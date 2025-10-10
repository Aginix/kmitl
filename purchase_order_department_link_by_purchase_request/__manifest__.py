# -*- coding: utf-8 -*-
{
    'name': 'Purchase Order Department Link By Purchase Request',
    'version': '16.0.1.0.0',
    'summary': """ Purchase Order Department Link By Purchase Request Summary """,
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "KMITL",
    'depends': ['purchase_request_department'],
    "data": [
        "security/ir.model.access.csv",
        "wizards/purchase_request_line_make_purchase_order.xml"
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
