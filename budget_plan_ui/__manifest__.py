# -*- coding: utf-8 -*-
{
    "name": "KMITL Budget Plan UI",
    "version": "16.0.1.0.0",
    "summary": """ Budget_plan_ui Summary """,
    "author": "Aginix Technologies",
    "website": "https://github.com/madara1150/budget",
    "category": "KMITL/Budgeting",
    "depends": [
        "base",
        "web",
        "budget_plan",
        "account_analytic_parent",
    ],
    "data": [
        "views/capital_expenditure_views.xml",
        "security/ir.model.access.csv",
        "views/budget_plan_views.xml",
    ],
    "assets": {
        "web.assets_backend": ["budget_plan_ui/static/src/**/*"],
    },
    "application": False,
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
