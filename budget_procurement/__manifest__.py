# -*- coding: utf-8 -*-
{
    'name': 'Budget_procurement',
    'version': '16.0.1.0.0',
    'summary': """ Budget_procurement Summary """,
    'author': '',
    'website': '',
    'category': '',
    'depends': ['base', 'web','budget_plan_ui'],
    "data": [
        "views/budget_appropriation_views.xml",
    ],
    'assets': {
              'web.assets_backend': [
                  'budget_procurement/static/src/**/*'
              ],
          },
    'application': False,
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
