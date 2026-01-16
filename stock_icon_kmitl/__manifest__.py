# -*- coding: utf-8 -*-
{
    'name': 'Stock Icon KMITL',
    'version': '16.0.1.0.0',
    'summary': """ Stock Icon KMITL Summary """,
    "category": "KMITL",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    'depends': ['stock'],
    'data': [
        "views/stock.xml"
    ],
    'assets': {
              'web.assets_backend': [
                  'stock_icon_kmitl/static/src/**/*'
              ],
          },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
