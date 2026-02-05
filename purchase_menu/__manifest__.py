# -*- coding: utf-8 -*-
{
    'name': 'Purchase Menu Custom',
    'version': '16.0.1.0.0',
    'summary': """ Purchase Menu Summary """,
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "Purchase",
    'depends': ['purchase_guarantee_kmitl', 'purchase_work_acceptance_kmitl', 'l10n_th_gov_account_asset_management', 'purchase_contract_kmitl'],
    'data': [
        'views/purchase_order_tree_expiring.xml',
        'views/purchase_tracking.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
