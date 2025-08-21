# -*- coding: utf-8 -*-
{
    'name': 'Kmitl_purchase_guarantee',
    'version': '16.0.1.0.0',
    'summary': """ Kmitl_purchase_guarantee Summary """,
    'author': '',
    'website': '',
    'category': '',
    'depends': ['base', 'web', 'l10n_th_gov_purchase_guarantee', 'kmitl_purchase_agreement'],
    "data": [
        "data/purchase_guarantee_method_data.xml",
        "data/purchase_guarantee_rules.xml",
        "data/purchase_guarantee_sequence.xml",
        "data/purchase_guarantee_type_data.xml",
        "security/ir.model.access.csv",
        "views/agreement_views.xml",
        "views/purchase_guarantee_attachment_views.xml",
        "views/purchase_guarantee_views.xml"
    ],
    'assets': {
              'web.assets_backend': [
                  'kmitl_purchase_guarantee/static/src/**/*'
              ],
          },
    'application': True,
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
