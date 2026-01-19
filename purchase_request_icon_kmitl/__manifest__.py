# -*- coding: utf-8 -*-
{
    'name': 'Purchase Request Icon KMITL',
    'version': '16.0.1.0.0',
    'summary': """ Purchase Request Icon KMITL Summary """,
    "category": "KMITL",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    'depends': ['purchase_request'],
    'data': [
        "views/purchase_request.xml"
    ],
    'assets': {
              'web.assets_backend': [
                  'purchase_request_icon_kmitl/static/src/**/*'
              ],
          },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
