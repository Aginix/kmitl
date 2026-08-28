# -*- coding: utf-8 -*-
{
    'name': 'Purchase Team',
    'version': '16.0.1.0.0',
    'summary': """ Purchase Team Summary """,
    "category": "KMITL",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    # missing PA ou
    'depends': ['purchase_request_department_operating_unit', 'purchase_order_department_operating_unit', 'purchase_request_approval', 'purchase_request_security'],
    "data": [
        "security/ir.model.access.csv",
        "data/purchase.team.csv",
        "views/purchase_order_views.xml",
        "views/purchase_request_approval_views.xml",
        "views/purchase_request_views.xml",
        "views/purchase_team_views.xml"
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
