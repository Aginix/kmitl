# -*- coding: utf-8 -*-
{
    'name': 'Purchase Request Approval Tier Validation',
    'version': '16.0.1.0.0',
    'summary': """ Purchase Request Approval Tier Validation""",
    'author': 'Aginix Techonologies',
    'website': 'https://github.com/aginix/kmitl',
    'category': 'KMITL',
    'depends': ['base_tier_validation', 'purchase_request_approval'],
    "data": [
        "views/purchase_request_approval_views.xml"
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
