# -*- coding: utf-8 -*-
{
    'name': 'Purchase Work Acceptance Portal',
    'version': '16.0.1.0.0',
    'summary': """ Purchase Work Acceptance Portal Summary """,
    "category": "KMITL",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    'depends': [
        'purchase_work_acceptance_kmitl',
        'purchase_order_kmitl',
        'portal',
        'mail_activity_todo',
    ],
    "data": [
        "data/mail_activity_type_data.xml",
        "views/purchase_order_portal_template.xml",
        "views/work_acceptance_portal_template.xml",
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
