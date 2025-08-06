# -*- coding: utf-8 -*-
{
    'name': 'Kmitl_purchase_request_tier_validation',
    'version': '16.0.1.0.0',
    'summary': """ Kmitl_purchase_request_tier_validation Summary """,
    'author': '',
    'website': '',
    'category': '',
    'depends': ['base', 'web', 'base_tier_validation', 'kmitl_purchase_request'],
    "data": [
        "security/security.xml",
        'security/purchase_request_rules.xml',
        'security/ir.model.access.csv',
        "views/purchase_request_views.xml"
    ],
    'assets': {
              'web.assets_backend': [
                  'kmitl_purchase_request_tier_validation/static/src/**/*'
              ],
          },
    'application': True,
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
