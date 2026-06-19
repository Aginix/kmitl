# -*- coding: utf-8 -*-
{
    'name': 'Purchase Guarantee Kmitl',
    'version': '16.0.1.0.0',
    'summary': """ Purchase Guarantee Kmitl Summary """,
    'author': 'Aginix Technologies',
    'website': 'https://github.com/aginix/kmitl',
    'category': 'KMITL',
    'depends': ['l10n_th_gov_purchase_guarantee', 'purchase_exception', 'purchase_budget'],
    "data": [
        "data/mail_activity_type.xml",
        "data/ir_cron_data.xml",
        "data/purchase_guarantee_method_data.xml",
        "data/purchase_exception.xml",
        "data/purchase_guarantee_rules.xml",
        "data/purchase_guarantee_type_data.xml",
        "views/purchase_guarantee_action.xml",
        "views/purchase_guarantee_views.xml",
        "views/account_move_views.xml",
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
