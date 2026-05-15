{
    "name": "Budget Appropriation Summary Dashboard",
    "version": "16.0.1.0.0",
    "summary": "Interactive portal dashboard for budget appropriation overview",
    "category": "KMITL/Budgeting",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "depends": [
        "budget_appropriation_summary",
        "portal",
    ],
    "data": [
        "views/portal_summary_templates.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "budget_appropriation_summary_dashboard/static/src/portal_summary/**/*",
        ],
    },
    "auto_install": False,
    "application": False,
    "installable": True,
    "license": "AGPL-3",
}
