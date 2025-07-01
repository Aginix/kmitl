# -*- coding: utf-8 -*-
{
    "name": "Budget Procurement Plan",
    "version": "16.0.1.0.0",
    "summary": """ Budget Procurement Plan Summary """,
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "KMITL/Budgeting",
    "depends": ["web", "procurement_plan", "budget"],
    "data": [
        "data/budget_account_procurement_update.xml",
        "views/budget_move_line_views.xml",
        "views/budget_move_views.xml",
        "views/budget_account_views.xml",
        "views/procurement_plan_views.xml",
        "views/procurement_plan_menu.xml",
    ],
    "assets": {
        "web.assets_backend": ["budget_procurement_plan/static/src/**/*"],
    },
    "application": False,
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
