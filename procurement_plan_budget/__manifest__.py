# -*- coding: utf-8 -*-
{
    "name": "Procurement Plan Budget",
    "version": "16.0.1.0.0",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "KMITL",
    "depends": ["budget", "budget_appropriation", "procurement_plan", "web"],
    "data": [
        "views/budget_account_views.xml",
        "views/budget_appropriation_views.xml",
        "views/budget_commitment_views.xml",
        "views/budget_move_views.xml",
        "views/procurement_plan_menu.xml",
        "views/procurement_plan_views.xml",
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
