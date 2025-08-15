# -*- coding: utf-8 -*-
{
    'name': 'Kmitl Purchase Order',
    'version': '16.0.1.0.0',
    'summary': """ Kmitl Purchase Order """,
    'author': 'Aginix Techonologies',
    'website': 'https://github.com/aginix/kmitl',
    'category': 'KMITL',
    'depends': ['kmitl_purchase_request_2', 'purchase_invoice_plan', 'purchase_no_rfq'],
    "data": [
        "data/purchase_order_sequence.xml",
        "security/ir.model.access.csv",
        "views/purchase_create_invoice_plan_views.xml",
        "views/purchase_exception_views.xml",
        "views/purchase_invoice_inherit_views.xml",
        "views/purchase_invoice_plan_views.xml",
        "views/purchase_order_attachment_views.xml",
        "views/purchase_order_bidder_line_views.xml",
        "views/purchase_order_views.xml",
        "views/purchase_request_two_views.xml",
        "views/purchase_requisition_views.xml"
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
