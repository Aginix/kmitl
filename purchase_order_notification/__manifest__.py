# -*- coding: utf-8 -*-
{
    'name': 'Purchase Order Notification',
    'version': '16.0.1.0.0',
    'summary': """ Purchase Order Notification Summary """,
    "category": "Aginix",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    'depends': ['purchase_menu'],
    "data": [
        "data/ir_cron_data.xml",
        "views/res_config_settings_views.xml"
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
