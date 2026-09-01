# -*- coding: utf-8 -*-
{
    "name": "Procurement Plan Viewer",
    "version": "16.0.1.0.0",
    "summary": "Read-only access to procurement plans",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "KMITL",
    "depends": ["procurement_plan"],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "views/menus.xml",
    ],
    "application": False,
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
