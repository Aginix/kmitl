# -*- coding: utf-8 -*-
{
    "name": "Project_proposal",
    "version": "16.0.1.0.0",
    "summary": """ Project_proposal Summary """,
    "author": "Aginix Technology",
    "website": "",
    "category": "",
    "depends": ["base", "web", "project"],
    "data": [
        "security/ir.model.access.csv",
        "views/project_kmitl_views.xml",
    ],
    "assets": {
        "web.assets_backend": ["project_proposal/static/src/**/*"],
    },
    "application": True,
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
