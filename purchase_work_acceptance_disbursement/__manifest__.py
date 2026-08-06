# -*- coding: utf-8 -*-
{
    'name': 'Purchase Work Acceptance Disbursement',
    'version': '16.0.1.2.0',
    'summary': """ Purchase Work Acceptance Disbursement Summary """,
    "category": "KMITL",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    'depends': [
        'purchase_work_acceptance_kmitl',
        'purchase_work_acceptance_invoice_plan',
        'purchase_order_disbursement',
    ],
    "data": [
        "views/disbursement_request_views.xml",
        "views/purchase_order_views.xml",
        "views/work_acceptance_views.xml"
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
