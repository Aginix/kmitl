# -*- coding: utf-8 -*-
{
    'name': 'Kmitl_purchase_order',
    'version': '16.0.1.0.0',
    'summary': """ Kmitl_purchase_order Summary """,
    'author': '',
    'website': '',
    'category': '',
    'depends': ['base', 'web', 'kmitl_purchase_request', 'kmitl_purchase_request_2_new', 'purchase_invoice_plan', 'purchase_no_rfq'],
    "data": [
        "data/purchase_order_sequence.xml",
        "security/ir.model.access.csv",
        "views/purchase_invoice_inherit_views.xml",
        "views/purchase_create_invoice_plan_views.xml",
        "views/purchase_order_attachment_views.xml",
        "views/purchase_order_bidder_line_views.xml",
        "views/purchase_order_views.xml"
    ],
    'assets': {
              'web.assets_backend': [
                  'kmitl_purchase_order/static/src/**/*'
              ],
          },
    'application': True,
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
