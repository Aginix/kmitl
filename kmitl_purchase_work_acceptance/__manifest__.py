# -*- coding: utf-8 -*-
{
    'name': 'Kmitl_purchase_work_acceptance',
    'version': '16.0.1.0.0',
    'summary': """ Kmitl_purchase_work_acceptance Summary """,
    'author': '',
    'website': '',
    'category': '',
    'depends': ['base', 'web', 'purchase_work_acceptance', 'kmitl_purchase_agreement'],
    "data": [
        "security/ir.model.access.csv",
        "views/agreement_views.xml",
        "views/purchase_work_acceptance_attachment_views.xml",
        "views/work_acceptance_views.xml"
    ],
    'assets': {
              'web.assets_backend': [
                  'kmitl_purchase_work_acceptance/static/src/**/*'
              ],
          },
    'application': True,
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
