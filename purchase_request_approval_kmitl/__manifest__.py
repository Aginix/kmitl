# -*- coding: utf-8 -*-
{
    'name': 'Purchase Request Approval KMITL',
    'version': '16.0.1.0.0',
    'summary': """ Purchase Request Approval Kmitl Summary """,
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "KMITL",
    'depends': ['l10n_th_gov_purchase_request', 'purchase_request_budget', 'purchase_request_security', 'purchase_request_tier_validation'],
    "data": [
        "data/substate.xml",
        "data/tier_definition.xml",
        "security/purchase_request_group.xml",
        "views/purchase_request_views.xml",
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
