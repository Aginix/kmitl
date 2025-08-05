# -*- coding: utf-8 -*-
{
    'name': 'Purchase_request_kmitl_form',
    'version': '16.0.1.0.0',
    'summary': """ Purchase_request_kmitl_form Summary """,
    'author': '',
    'website': '',
    'category': '',
    'depends': ['purchase_request_kmitl', 'purchase_no_rfq'],
    "data": [
        "data/purchase_request_kmitl_form_sequence.xml",
        "data/purchase_request_kmitl_submit_sequence.xml",
        "data/purchase_order_seq.xml",
        "security/ir.model.access.csv",
        "views/purchase_request_views.xml",
        "views/purchase_order_views.xml",
        "views/purchase_request_form_line_views.xml",
        "views/purchase_request_form_views.xml",
        "views/purchase_request_submit_line_views.xml",
        "views/purchase_request_submit_views.xml",
    ],
    'assets': {
              'web.assets_backend': [
                  'purchase_request_kmitl_form/static/src/**/*'
              ],
          },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
