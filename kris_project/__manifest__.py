# -*- coding: utf-8 -*-
{
    "name": "KRIS Project",
    "version": "16.0.1.0.0",
    "category": "Project",
    "summary": "Academic service and research project revenue tracking for KRIS",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "depends": [
        "mail",
        "hr",
        "account_fiscal_year",
    ],
    "data": [
        "data/sequence.xml",
        "security/security.xml",
        "security/ir.model.access.csv",
        "views/kris_project_views.xml",
        "views/kris_project_menus.xml",
    ],
    "application": True,
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
