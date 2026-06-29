# -*- coding: utf-8 -*-
{
    'name': 'Purchase Guarantee Expiration',
    'version': '16.0.1.0.0',
    'summary': """ Purchase Guarantee Expiration Summary """,
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "Purchase",
    'depends': ['purchase_kmitl', 'purchase_guarantee_kmitl', 'mail_activity_todo'],
    'data': [
        "data/mail_activity_type_data.xml",
        "data/ir_cron_data.xml",
        "views/view.xml",
        "views/res_config_settings_views.xml",
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
