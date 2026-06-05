# -*- coding: utf-8 -*-
{
    "name": "Procurement Plan Budget Appropriation",
    "version": "16.0.1.1.0",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "KMITL",
    "depends": ["budget_appropriation", "procurement_plan", "budget_appropriation_summary", "web"],
    "data": [
        "views/budget_appropriation_views.xml",
        "views/procurement_plan_views.xml",
        "views/budget_appropriation_compilation_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "procurement_plan_budget/static/src/**/*",
        ],
    },
    "application": False,
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
