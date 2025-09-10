# -*- coding: utf-8 -*-
{
    'name': 'Purchase Guarantee No Invoice Bill',
    'version': '16.0.1.0.0',
    'summary': """ Purchase Guarantee No Invoice Bill """,
    'author': 'Aginix Technologies',
    'website': 'https://github.com/aginix/kmitl',
    'category': 'KMITL',
    'depends': ['l10n_th_gov_purchase_guarantee'],
    "data": [
        "views/account_move_views.xml",
        "views/purchase_guarantee_views.xml"
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
