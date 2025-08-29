# -*- coding: utf-8 -*-
{
    'name': 'Purchase Work Acceptance Tier Validation KMITL',
    'version': '16.0.1.0.0',
    'summary': """ Purchase Work Acceptance Tier Validation System for KMITL """,
    'author': 'Aginix Techonologies',
    'website': 'https://github.com/aginix/kmitl',
    'category': 'KMITL',
    'depends': ['base', 'web', 'purchase_work_acceptance_tier_validation', 'purchase_work_acceptance_kmitl'],
    "data": [
        "views/work_acceptance_views.xml"
    ],
    'assets': {
              'web.assets_backend': [
                  'kmitl_purchase_work_acceptance_tier_validation/static/src/**/*'
              ],
          },
    'application': True,
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
