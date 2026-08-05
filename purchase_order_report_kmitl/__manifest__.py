# -*- coding: utf-8 -*-
{
    'name': 'Purchase Order Report KMITL',
    'version': '16.0.1.0.0',
    'summary': """ Purchase Order Report KMITL Summary """,
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "KMITL",
    'depends': ['purchase_request', 'thai_date_utils', 'purchase_contract_kmitl', 'purchase_order_link_purchase_request', 'hr', 'l10n_th_amount_to_text'],
    'data': [
        "security/ir.model.access.csv",
        "reports/report_purchase_order.xml",
        "reports/paperformat_purchase_order.xml",
        "wizards/material_withdrawal_wizard_views.xml",
        "reports/report_material_withdrawal.xml",
        "views/purchase_order_views.xml",
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
