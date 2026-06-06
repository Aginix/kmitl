# -*- coding: utf-8 -*-
{
    "name": "e-Sarabun",
    "summary": "Electronic Correspondence Management System (สารบรรณอิเล็กทรอนิกส์)",
    "version": "16.0.2.0.0",
    "category": "KMITL/Correspondence",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    # P1 (core data model) deps only. portal/bus/iframe/fonts/amount-to-text are
    # re-added with their phases (P4 notifications/access, P5 signing/report).
    "depends": ["mail", "hr", "thai_date_utils"],
    "data": [
        # Security
        "security/security.xml",
        "security/ir.model.access.csv",
        # Master data
        "data/sarabun_document_type.xml",
        # Views
        "views/sarabun_document_type_views.xml",
        "views/sarabun_position_views.xml",
        "views/sarabun_document_views.xml",
        "views/sarabun_menus.xml",
    ],
    "application": True,
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
