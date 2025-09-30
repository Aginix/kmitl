# -*- coding: utf-8 -*-
{
    "name": "Project KMITL",
    "version": "16.0.1.0.0",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "KMITL",
    "depends": ["project", "hr", "account_fiscal_year"],
    "data": [
        "data/project.fight.csv",
        "data/project.global.index.csv",
        "data/project.impact.csv",
        "data/project.methodology.csv",
        "data/project.strategic.plan.csv",
        "data/project.evaluation.csv",
        "security/ir.model.access.csv",
        "views/menus.xml",
        "views/project_evaluation_views.xml",
        "views/project_fight_views.xml",
        "views/project_global_index_views.xml",
        "views/project_impact_views.xml",
        "views/project_methodology_views.xml",
        "views/project_project_views.xml",
        "views/project_strategic_plan_views.xml"
    ],
    "assets": {
        "web.assets_backend": [
            "project_kmitl/static/src/components/**/*",
        ],
    },
    "application": False,
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
