# -*- coding: utf-8 -*-
{
    'name': 'Purchase Guarantee KMITL',
    'version': '16.0.1.0.0',
    'summary': """ Purchase Guarantee System for KMITL """,
    'author': 'Aginix Techonologies',
    'website': 'https://github.com/aginix/kmitl',
    'category': 'KMITL',
    'depends': ['base', 'web', 'l10n_th_gov_purchase_guarantee', 'purchase_agreement_kmitl'],
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
                  'purchase_guarantee_kmitl/static/src/**/*'
              ],
          },
    'application': True,
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
