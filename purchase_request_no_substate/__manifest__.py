# -*- coding: utf-8 -*-
{
    'name': 'Purchase Request No Substate',
    'version': '16.0.1.0.0',
    'summary': """ Purchase Request No Substate Summary """,
    "category": "KMITL",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    'depends': ['l10n_th_gov_purchase_request'],
    "data": [
        "data/disable_substates.xml",
        "views/purchase_request_views.xml",
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
