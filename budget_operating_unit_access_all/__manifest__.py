# -*- coding: utf-8 -*-
{
    'name': 'Budget_operating_unit_access_all',
    'version': '16.0.1.0.0',
    'summary': """ Budget_operating_unit_access_all Summary """,
    'author': '',
    'website': '',
    'category': '',
    'depends': ['budget_operating_unit'],
    'data': [
        "security/budget_security.xml",
    ],
    'assets': {
              'web.assets_backend': [
                  'budget_operating_unit_access_all/static/src/**/*'
              ],
          },
    'installable': True,
    'license': 'LGPL-3',
}
