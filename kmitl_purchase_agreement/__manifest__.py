# -*- coding: utf-8 -*-
{
    'name': 'Kmitl purchase agreement',
    'version': '16.0.1.0.0',
    'summary': """ Kmitl_purchase_agreement Summary """,
    'author': '',
    'website': '',
    'category': '',
    'depends': ['agreement_legal', 'kmitl_purchase_order'],
    "data": [
        "security/ir.model.access.csv",
        "views/agreement_views.xml",
        "views/purchase_order_views.xml",
        "wizards/agreement_new_version_wizard.xml"
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
