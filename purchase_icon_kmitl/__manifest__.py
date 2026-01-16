# -*- coding: utf-8 -*-
{
    'name': 'Purchase Icon KMITL',
    'version': '16.0.1.0.0',
    'summary': """ Purchase Icon KMITL Summary """,
    "category": "KMITL",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    'depends': ['purchase'],
    'data': [
        "views/purchase.xml"
    ],
    'assets': {
              'web.assets_backend': [
                  'purchase_icon_kmitl/static/src/**/*'
              ],
          },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
