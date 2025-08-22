# -*- coding: utf-8 -*-
{
    'name': 'Kmitl Purchase Work Acceptance',
    'version': '16.0.1.0.0',
    'summary': """ Kmitl Purchase Work Acceptance Summary """,
    'author': 'Aginix Techonologies',
    'website': 'https://github.com/aginix/kmitl',
    'category': 'KMITL',
    'depends': ['purchase_work_acceptance', 'kmitl_purchase_agreement', 'purchase_work_acceptance_invoice_plan'],
    "data": [
        "security/ir.model.access.csv",
        "views/agreement_views.xml",
        "views/purchase_order_views.xml",
        "views/purchase_work_acceptance_attachment_views.xml",
        "views/select_work_acceptance_invoice_plan_wizard_views.xml",
        "views/work_acceptance_views.xml"
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
