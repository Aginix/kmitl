# -*- coding: utf-8 -*-
{
    'name': 'Budget Appropriation Report',
    "version": "16.0.1.0.0",
    "summary": "Budget Appropriation Report",
    "category": "KMITL/Budgeting",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "depends": ["budget_appropriation", "web"],
    "data": [
        "data/budget_appropriation_report_action.xml",
        "security/ir.model.access.csv",
        "report/budget_appropriation_report_templates.xml",
        "report/budget_appropriation_report_actions.xml",
        "views/menus.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "budget_appropriation_report/static/src/**/*",
        ],
    },
    "auto_install": False,
    "application": False,
    "installable": True,
    "license": "AGPL-3",
}
