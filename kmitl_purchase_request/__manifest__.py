# -*- coding: utf-8 -*-
{
    'name': 'Kmitl Purchase Request',
    'version': '16.0.1.0.0',
    'summary': """ Kmitl Purchase Request""",
    "category": "KMITL",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    'depends': ['l10n_th_gov_purchase_request', 'l10n_th_base_sequence'],
    "data": [
        "security/purchase_request.xml",
        "security/ir.model.access.csv",
        "data/purchase_request_sequence.xml",
        "data/purchase_request_rules.xml",
        "data/purchase_request_exception.xml",
        "views/purchase_request_attachment_views.xml",
        "views/purchase_request_views.xml"
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
