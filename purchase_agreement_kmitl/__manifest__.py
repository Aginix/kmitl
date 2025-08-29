# -*- coding: utf-8 -*-
{
    'name': 'Purchase Agreement KMITL',
    'version': '16.0.1.0.0',
    'summary': """ Purchase Agreement System for KMITL """,
    'author': 'Aginix Techonologies',
    'website': 'https://github.com/aginix/kmitl',
    'category': 'KMITL',
    'depends': ['l10n_th_gov_purchase_agreement', 'purchase_order_kmitl'],
    "data": [
        "security/ir.model.access.csv",
        "views/agreement_menu.xml",
        "views/agreement_views.xml",
        "views/purchase_order_views.xml",
        "wizards/agreement_new_version_wizard.xml"
    ],
    "assets": {
        'web.assets_backend': [
            'purchase_agreement_kmitl/static/src/css/template_inherit.css',
        ],
    },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
