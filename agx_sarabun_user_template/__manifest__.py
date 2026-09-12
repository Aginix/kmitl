# -*- coding: utf-8 -*-
{
    "name": "e-Sarabun: User Route Templates",
    "summary": (
        "Allow regular sarabun users to define their own route templates "
        "with personal/unit/public visibility (ADR-0016)"
    ),
    "version": "16.0.1.0.0",
    "category": "KMITL/Correspondence",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "depends": ["agx_sarabun"],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "views/sarabun_route_template_views.xml",
    ],
    "application": False,
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
