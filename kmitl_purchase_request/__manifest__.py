# -*- coding: utf-8 -*-
{
    'name': 'Kmitl_purchase_request',
    'version': '16.0.1.0.0',
    'summary': """ Kmitl_purchase_request Summary """,
    'author': '',
    'website': '',
    'category': '',
    'depends': ['base', 'web', 'purchase_request', 'hr', 'l10n_th_gov_purchase_request', 'purchase_request_exception'],
    "data": [
        "data/purchase_request_sequence.xml",
        "data/purchase_request_exception.xml",
        "security/security.xml",
        "security/ir.model.access.csv",
        "views/hr_employee_views.xml",
        "views/purchase_request_attachment_views.xml",
        "views/purchase_request_views.xml"
    ],
    'assets': {
              'web.assets_backend': [
                  'kmitl_purchase_request/static/src/**/*'
              ],
          },
    'application': True,
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
