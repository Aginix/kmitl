# -*- coding: utf-8 -*-
{
    "name": "e-Sarabun",
    "summary": "Electronic Correspondence Management System",
    "version": "16.0.1.0.0",
    "category": "KMITL/Correspondence",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "depends": ["mail", "hr"],
    "data": [
        # Security
        "security/security.xml",
        "security/ir.model.access.csv",
        # Data
        "data/sarabun_sequence.xml",
        "data/sarabun_document_type.xml",
        # Wizard
        "wizard/sarabun_routing_wizard_views.xml",
        # Views
        "views/sarabun_document_type_views.xml",
        "views/sarabun_route_template_views.xml",
        "views/sarabun_document_views.xml",
        "views/sarabun_routing_line_views.xml",
        "views/sarabun_document_sequence_views.xml",
        "views/sarabun_role_views.xml",
        "views/hr_department_views.xml",
        "views/sarabun_menus.xml",
    ],
    "application": True,
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
