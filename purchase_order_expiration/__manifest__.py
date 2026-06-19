# -*- coding: utf-8 -*-
{
    'name': 'Purchase Order Exipration',
    'version': '16.0.1.0.0',
    'summary': """ Purchase Order Exipration Summary """,
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "Purchase",
    'depends': ['purchase_kmitl', 'purchase_contract_kmitl'],
    "data": [
        "data/mail_activity_type.xml",
        "data/ir_cron_data.xml",
        "views/purchase_order_views.xml",
        "views/res_config_settings_views.xml"
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
