# -*- coding: utf-8 -*-
{
    'name': 'Kris Project Revision',
    'version': '16.0.1.0.0',
    'summary': """ Kris Project Revision Summary """,
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    'category': '',
    'depends': ['kris_project', 'base_revision'],
    "data": [
        "views/kris_project_views.xml"
    ],
    'assets': {
              'web.assets_backend': [
                  'kris_project_revision/static/src/**/*'
              ],
          },
    'application': True,
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
    "post_init_hook": "populate_unrevisioned_name",
}
