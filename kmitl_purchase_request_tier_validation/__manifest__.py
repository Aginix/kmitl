# -*- coding: utf-8 -*-
{
    'name': 'Kmitl Purchase Request Tier Validation',
    'version': '16.0.1.0.0',
    'summary': """ Kmitl Purchase Request Tier Validation""",
    "category": "KMITL",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    'depends': ['base_tier_validation', 'kmitl_purchase_request'],
    "data": [
        "views/purchase_request_views.xml",
        # "templates/tier_validation_templates.xml"
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
