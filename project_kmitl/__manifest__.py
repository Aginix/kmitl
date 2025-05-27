# -*- coding: utf-8 -*-
{
    'name': 'Project_kmitl',
    'version': '16.0.1.0.0',
    'summary': """ Project_kmitl Summary """,
    'author': '',
    'website': '',
    'category': '',
    'depends': ['base', 'web', 'project', 'hr', 'account_fiscal_year'],
    "data": [
        "security/ir.model.access.csv",
        "data/project.strategic.plan.csv",
        "views/project_project_views.xml",
    ],
    'assets': {
              'web.assets_backend': [
                  'project_kmitl/static/src/**/*'
              ],
          },
    'application': True,
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
