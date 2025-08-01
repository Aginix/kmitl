# -*- coding: utf-8 -*-
{
    'name': 'Kmitl_purchase_request_2_new',
    'version': '16.0.1.0.0',
    'summary': """ Kmitl_purchase_request_2_new Summary """,
    'author': '',
    'website': '',
    'category': '',
    'depends': ['base', 'web', 'kmitl_purchase_request'],
    "data": [
        "data/purchase_request_two_sequence.xml",
        "security/ir.model.access.csv",
        "views/purchase_request_two_line_views.xml",
        "views/purchase_request_two_submitted_line_views.xml",
        "views/purchase_request_two_submitted_views.xml",
        "views/purchase_request_two_views.xml",
        "views/purchase_request_views.xml"
    ],
    'assets': {
              'web.assets_backend': [
                  'kmitl_purchase_request_2_new/static/src/**/*'
              ],
          },
    'application': True,
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
