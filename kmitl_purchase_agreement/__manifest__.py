# -*- coding: utf-8 -*-
{
    'name': 'Kmitl purchase agreement',
    'version': '16.0.1.0.0',
    'summary': """ Kmitl_purchase_agreement Summary """,
    'author': '',
    'website': '',
    'category': '',
    'depends': ['base', 'web', 'agreement_legal', 'kmitl_purchase_order'],
    "data": [
        "security/ir.model.access.csv",
        "views/agreement_views.xml",
        "views/purchase_order_views.xml"
    ],
    'assets': {
              'web.assets_backend': [
                  'kmitl_purchase_agreement/static/src/**/*'
              ],
          },
    'application': True,
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
