# -*- coding: utf-8 -*-
{
    'name': 'Purchase Work Acceptance Kmitl',
    'version': '16.0.1.0.0',
    'summary': """ Purchase Work Acceptance Kmitl Summary """,
    "category": "KMITL",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    'depends': [
        'purchase_work_acceptance_cancel_restriction',
        'purchase_work_acceptance_external',
        'base_tier_validation_comment',
    ],
    "data": [
        "data/server_action.xml",
        "data/tier.definition.csv",
        "security/ir.model.access.csv",
        "views/purchase_order_views.xml",
        "views/work_acceptance_views.xml",
        "wizards/work_acceptance_committee_wizard.xml"
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
