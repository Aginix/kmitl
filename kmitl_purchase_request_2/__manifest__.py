# -*- coding: utf-8 -*-
{
    'name': 'Kmitl Purchase Request 2',
    'version': '16.0.1.0.0',
    'summary': """ Kmitl Purchase Request 2""",
    'author': 'Aginix Techonologies',
    'website': 'https://github.com/aginix/kmitl',
    'category': 'KMITL',
    'depends': ['purchase_request_kmitl', 'l10n_th_base_sequence'],
    "data": [
        "data/purchase_request_two_sequence.xml",
        "data/res_partner.xml",
        "security/ir.model.access.csv",
        "views/purchase_request_two_views.xml",
        "views/purchase_request_two_line_views.xml",
        "views/purchase_request_two_submitted_line_views.xml",
        "views/purchase_request_two_submitted_views.xml",
        "views/purchase_request_views.xml"
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
