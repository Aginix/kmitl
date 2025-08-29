# -*- coding: utf-8 -*-
{
    'name': 'Purchase Work Acceptance KMITL',
    'version': '16.0.1.0.0',
    'summary': """ Purchase Work Acceptance System for KMITL """,
    'author': 'Aginix Techonologies',
    'website': 'https://github.com/aginix/kmitl',
    'category': 'KMITL',
    'depends': ['purchase_work_acceptance', 'purchase_agreement_kmitl', 'purchase_work_acceptance_invoice_plan'],
    "data": [
        "security/ir.model.access.csv",
        "views/agreement_views.xml",
        "views/purchase_invoice_plan_views.xml",
        "views/purchase_order_views.xml",
        "views/purchase_work_acceptance_attachment_views.xml",
        "views/select_work_acceptance_invoice_plan_wizard_views.xml",
        "views/work_acceptance_views.xml",
        "views/work_accepted_date_wizard_views.xml"
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
