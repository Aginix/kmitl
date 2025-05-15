# -*- coding: utf-8 -*-
{
    'name': 'Budget_procurement_plan',
    'version': '16.0.1.0.0',
    'summary': """ Budget_procurement_plan Summary """,
    'author': '',
    'website': '',
    'category': '',
    'depends': ['base', 'web', 'procurement_plan', 'budget'],
    "data": [
        "views/budget_appropriation_line_views.xml",
        "views/budget_appropriation_views.xml",
        "views/budget_template_form_views.xml",
        "views/budget_template_line_views.xml",
        "views/procurement_plan_views.xml"
    ],
    'assets': {
              'web.assets_backend': [
                  'budget_procurement_plan/static/src/**/*'
              ],
          },
    'application': False,
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
