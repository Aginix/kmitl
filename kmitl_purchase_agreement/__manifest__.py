# -*- coding: utf-8 -*-
{
    'name': 'Kmitl purchase agreement',
    'version': '16.0.1.0.0',
    'summary': """ Kmitl Purchase Agreement Summary """,
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
            'kmitl_purchase_agreement/static/src/css/template_inherit.css',
        ],
    },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
