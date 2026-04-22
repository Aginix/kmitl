# -*- coding: utf-8 -*-
{
    'name': 'Aginix Leadtime',
    'version': '16.0.1.0.0',
    'summary': """ Mixin for tracking leadtime between state transitions """,
    "category": "Tools",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    'depends': ['base', 'web'],
    'data': [
        'views/state_leadtime_log_views.xml',
        'security/ir.model.access.csv',
    ],
    'assets': {
              'web.assets_backend': [
                  'agx_leadtime/static/src/**/*'
              ],
          },
    'application': True,
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
