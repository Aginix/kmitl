# -*- coding: utf-8 -*-
{
    'name': 'Purchase Work Acceptance Kmitl',
    'version': '16.0.1.0.0',
    'summary': """ Purchase Work Acceptance Kmitl Summary """,
    "category": "KMITL",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    'depends': [
        'l10n_th_gov_work_acceptance',
        'base_tier_validation_comment',
        'purchase_work_acceptance',
        'purchase_work_acceptance_late_fines',
    ],
    "data": [
        "data/server_action.xml",
        "data/tier.definition.csv",
        "views/purchase_order_views.xml",
        "views/work_acceptance_views.xml",
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
