# -*- coding: utf-8 -*-
{
    'name': 'Purchase_request_attachment',
    'version': '16.0.1.0.0',
    'summary': """ Purchase_request_attachment Summary """,
    'author': '',
    'website': '',
    'category': '',
    'depends': ['purchase_request_kmitl'],
    "data": [
        "security/ir.model.access.csv",
        "views/purchase_request_attachment_views.xml",
        "views/purchase_request_views.xml"
    ],
    'assets': {
              'web.assets_backend': [
                  'purchase_request_attachment/static/src/**/*'
              ],
          },
    'application': True,
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
