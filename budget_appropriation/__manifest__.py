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
        "views/budget_move_views.xml",
        "data/budget_appropriation_sequence.xml",
        "data/budget_appropriation_f5_action.xml",
        "data/budget_appropriation_f5_pdf_report.xml",
        "report/budget_appropriation_f5_report_templates.xml",
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
