# -*- coding: utf-8 -*-
{
    'name': 'Merage PDF',
    'version': '16.0.1.0.0',
    'summary': """ Merage PDF Summary """,
    'author': '',
    'website': '',
    'category': '',
    'depends': ['purchase_request', 'purchase_order_report_kmitl', 'purchase_order_link_purchase_request','purchase_request_sarabun'],
    "data": [
        "views/purchase_order_views.xml",
        "views/purchase_request_views.xml"
    ],
    'application': True,
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
