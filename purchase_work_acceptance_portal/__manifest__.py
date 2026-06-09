# -*- coding: utf-8 -*-
{
    'name': 'Purchase Work Acceptance Portal',
    'version': '16.0.1.0.0',
    'summary': """ Purchase Work Acceptance Portal Summary """,
    "category": "KMITL",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    'depends': ['purchase_work_acceptance_kmitl', 'purchase_kmitl', 'portal'],
    "data": [
        "security/ir.model.access.csv",
        "security/ir_rule.xml",
        "views/purchase_order_portal_template.xml",
        "views/work_acceptance_portal_template.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "purchase_work_acceptance_portal/static/src/js/wa_notification_handler.esm.js",
            "purchase_work_acceptance_portal/static/src/js/wa_systray.esm.js",
            "purchase_work_acceptance_portal/static/src/scss/wa_systray.scss",
            "purchase_work_acceptance_portal/static/src/xml/wa_systray.xml",
        ],
    },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
