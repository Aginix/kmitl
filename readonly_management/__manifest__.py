# -*- coding: utf-8 -*-
{
    "name": "Readonly Management",
    "version": "16.0.1.0.0",
    "summary": "Centralized readonly field management via admin UI",
    "category": "KMITL/Technical",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "depends": ["base"],
    "data": [
        "security/ir.model.access.csv",
        "views/readonly_management_views.xml",
        "views/menus.xml",
    ],
    "installable": True,
    "auto_install": False,
    "license": "AGPL-3",
}
