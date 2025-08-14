# -*- coding: utf-8 -*-
{
    'name': 'Kmitl Purchase Request 2 Tier Validation',
    'version': '16.0.1.0.0',
    'summary': """ Kmitl Purchase Request 2 Tier Validation """,
    'author': 'Aginix Techonologies',
    'website': 'https://github.com/aginix/kmitl',
    'category': 'KMITL',
    'depends': ['base_tier_validation', 'kmitl_purchase_request_2'],
    "data": [
        "demo/tier_definition.xml",
        "views/purchase_request_two_submitted_views.xml"
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
