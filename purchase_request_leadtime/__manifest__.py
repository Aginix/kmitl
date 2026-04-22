# -*- coding: utf-8 -*-
{
    'name': 'Purchase Request Leadtime',
    'version': '16.0.1.0.0',
    'summary': """ Purchase Request Leadtime Summary """,
    "category": "KMITL",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    'depends': ['agx_leadtime', 'purchase_request_kmitl'],
    'data': [
        
    ],
    'assets': {
              'web.assets_backend': [
                  'purchase_request_leadtime/static/src/**/*'
              ],
          },
    'application': True,
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
