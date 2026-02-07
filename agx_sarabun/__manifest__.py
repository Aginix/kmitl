# -*- coding: utf-8 -*-
{
    "name": "e-Sarabun",
    "summary": "Electronic Correspondence Management System",
    "version": "16.0.1.0.0",
    "category": "KMITL/Correspondence",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "depends": ["mail", "hr", 'portal', 'thai_date_utils', 'l10n_th_fonts', 'l10n_th_amount_to_text', 'iframe_viewer_widget', 'bus'],
    "data": [
        # Security
        "security/security.xml",
        "security/ir.model.access.csv",
        # Data
        "data/sarabun_sequence.xml",
        "data/sarabun_document_type.xml",
        "data/sarabun_role.xml",
        "report/paperformat.xml",
        "report/report_sarabun.xml",
        # Wizard
        "wizard/sarabun_routing_wizard_views.xml",
        "views/sarabun_document_recall_wizard_views.xml",
        # Views
        "views/portal_template.xml",
        "views/sarabun_document_type_views.xml",
        "views/sarabun_route_template_views.xml",
        "views/sarabun_document_views.xml",
        "views/sarabun_routing_line_views.xml",
        "views/sarabun_document_recipient_views.xml",
        "views/sarabun_document_sequence_views.xml",
        "views/sarabun_role_views.xml",
        "views/hr_department_views.xml",
        "views/sarabun_menus.xml",
    ],
    "assets": {
        'web.assets_frontend': [
            'agx_sarabun/static/src/js/sarabun_document_portal_sidebar.js',
        ],
        'web.assets_backend': [
            'agx_sarabun/static/src/js/sarabun_notification_handler.esm.js',
            'agx_sarabun/static/src/js/sarabun_systray.esm.js',
            'agx_sarabun/static/src/scss/sarabun_systray.scss',
            'agx_sarabun/static/src/xml/sarabun_systray.xml',
        ],
    },
    "application": True,
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
