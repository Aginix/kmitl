# -*- coding: utf-8 -*-
{
    'name': 'Agx Sarabun Portal',
    'version': '16.0.1.0.0',
    'summary': """ Agx Sarabun Portal Summary """,
    "category": "KMITL/Portal",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    'depends': ['agx_sarabun_report', 'portal'],
    'data': [
        'views/portal_template.xml',
        'views/sarabun_document_views.xml',
    ],
    "assets": {
        'web.assets_frontend': [
            'agx_sarabun_portal/static/src/js/sarabun_document_portal_sidebar.js',
        ],
    },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
