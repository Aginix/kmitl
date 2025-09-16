# -*- coding: utf-8 -*-
{
    "name": "Budget Appropriation Offset",
    "version": "",
    "author": "",
    "website": "",
    "category": "",
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
