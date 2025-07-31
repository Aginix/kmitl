# -*- coding: utf-8 -*-
{
    'name': 'Budget_operating_unit',
    'version': '16.0.1.0.0',
    'summary': """ Budget_operating_unit Summary """,
    'author': '',
    'website': '',
    'category': '',
    'depends': ['operating_unit' ,'budget'],
    "data": [
        "security/budget_security.xml",
        "views/budget_move_views.xml",
        "views/budget_transfer_views.xml"
    ],
    'assets': {
              'web.assets_backend': [
                  'budget_operating_unit/static/src/**/*'
              ],
          },
    'application': True,
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
