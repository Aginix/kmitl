# -*- coding: utf-8 -*-
{
    'name': 'Purchase_request_kmitl_form',
    'version': '16.0.1.0.0',
    'summary': """ Purchase_request_kmitl_form Summary """,
    'author': '',
    'website': '',
    'category': '',
    'depends': ['purchase_request_kmitl'],
    "data": [
        "views/purchase_request_views.xml"
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
