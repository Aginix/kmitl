# -*- coding: utf-8 -*-
{
    'name': 'Operating_unit_kmitl',
    'version': '16.0.1.0.0',
    'summary': """ Operating_unit_kmitl Summary """,
    'author': '',
    'website': '',
    'category': '',
    'depends': ['operating_unit'],
    'data': [
        "data/operating_unit_data.xml",
    ],
    'assets': {
              'web.assets_backend': [
                  'operating_unit_kmitl/static/src/**/*'
              ],
          },
    'application': True,
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
