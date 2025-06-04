# -*- coding: utf-8 -*-
{
    'name': 'Project_kmitl_revision',
    'version': '16.0.1.0.0',
    'summary': """ Project_kmitl_revision Summary """,
    'author': '',
    'website': '',
    'category': '',
    'depends': ['base', 'web', 'base_revision', 'project_kmitl'],
    "data": [
        "views/project_project_views.xml"
    ],
    'assets': {
              'web.assets_backend': [
                  'project_kmitl_revision/static/src/**/*'
              ],
          },
    'application': False,
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
