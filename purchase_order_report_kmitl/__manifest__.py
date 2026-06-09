# -*- coding: utf-8 -*-
{
    'name': 'Purchase Order Report KMITL',
    'version': '16.0.1.0.0',
    'summary': """ Purchase Order Report KMITL Summary """,
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "KMITL",
    'depends': ['purchase_request' , 'thai_date_utils', 'purchase_kmitl', 'purchase_order_link_purchase_request'],
    'data': [
        "reports/report_purchase_order.xml",
        "reports/paperformat_purchase_order.xml",
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
