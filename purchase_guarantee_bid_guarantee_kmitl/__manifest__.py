# -*- coding: utf-8 -*-
{
    'name': 'Purchase Guarantee Bid Guarantee Kmitl',
    'version': '16.0.1.1.0',
    'summary': """ Purchase guarantee bid guarantee kmitl Summary """,
    'author': 'Aginix Technologies',
    'website': 'https://github.com/aginix/kmitl',
    'category': 'KMITL',
    'depends': ['l10n_th_gov_purchase_guarantee', 'purchase_request'],
    "data": [
        # purchase_guarantee_rules.xml clears noupdate on the base module's
        # xmlids, so it must load BEFORE anything that writes to them.
        "data/purchase_guarantee_rules.xml",
        "data/purchase_guarantee_method_data.xml",
        "views/purchase_guarantee_views.xml",
        "views/purchase_request_views.xml"
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
