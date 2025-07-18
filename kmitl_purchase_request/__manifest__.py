# -*- coding: utf-8 -*-
{
    'name': 'Kmitl_purchase_request',
    'version': '16.0.1.0.0',
    'summary': """ Kmitl_purchase_request Summary """,
    'author': '',
    'website': '',
    'category': '',
    'depends': ['base', 'web', 'purchase_request', 'hr'],
    "data": [
        "data/procurement_method.xml",
        "data/procurement_type.xml",
        "data/purchase_type.xml",
        "security/ir.model.access.csv",
        "views/purchase_request_attachment_views.xml",
        "views/purchase_request_views.xml",
        "views/purchase_type_views.xml"
    ],
    'assets': {
              'web.assets_backend': [
                  'kmitl_purchase_request/static/src/**/*'
              ],
          },
    'application': True,
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
