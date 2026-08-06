# -*- coding: utf-8 -*-
{
    "name": "e-Sarabun: Admin Reset",
    "summary": "Admin-only reset of a หนังสือ back to draft, keeping its number and Route (ADR-0011)",
    "version": "16.0.1.0.0",
    "category": "KMITL/Correspondence",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "depends": [
        "agx_sarabun",
    ],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "wizard/sarabun_reset_wizard_views.xml",
        "views/sarabun_document_views.xml",
    ],
    "application": False,
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
