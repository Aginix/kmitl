# -*- coding: utf-8 -*-
{
    'name': 'Purchase Contract KMITL',
    'version': '16.0.1.0.0',
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "KMITL",
    'depends': ['hr_department_short_name', 'purchase_exception', 'purchase_invoice_plan', 'purchase_work_acceptance_kmitl'],
    "data": [
        "data/cron.xml",
        "data/purchase_contract_type.xml",
        "data/purchase_exception.xml",
        "security/ir.model.access.csv",
        "views/purchase_contract_type_views.xml",
        "views/purchase_order_views.xml",
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
