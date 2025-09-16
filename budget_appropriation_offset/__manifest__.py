# -*- coding: utf-8 -*-
{
    "name": "Budget Appropriation Offset",
    "version": "16.0.1.0.0",
    "category": "KMITL/Budgeting",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "depends": ["budget_appropriation"],
    "data": [
        "security/ir.model.access.csv",
        "views/budget_appropriation_offset_views.xml",
        "views/budget_appropriation_views.xml"
    ],
    "assets": {
        "web.assets_backend": [
            "budget_appropriation_offset/static/src/**/*",
        ],
    },
    "application": False,
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
