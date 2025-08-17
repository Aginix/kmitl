{
    "name": "Budget Appropriation",
    "version": "16.0.1.0.0",
    "summary": "Budget Appropriation Management",
    "category": "KMITL/Budgeting",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "depends": [
        "budget",
        "account_analytic_kmitl",
        "mail",
    ],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "views/budget_appropriation_views.xml",
        "views/budget_appropriation_menus.xml",
        "data/budget_appropriation_sequence.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "budget_appropriation/static/src/**/*",
        ],
    },
    "auto_install": False,
    "application": False,
    "installable": True,
    "license": "AGPL-3",
}