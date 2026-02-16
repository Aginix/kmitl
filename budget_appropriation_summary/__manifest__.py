{
    "name": "Budget Appropriation Summary",
    "version": "16.0.1.0.0",
    "summary": "Compilation and master summary for budget appropriations",
    "category": "KMITL/Budgeting",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "depends": ["budget_appropriation", "mail"],
    "data": [
        "security/ir.model.access.csv",
        "views/budget_appropriation_compilation_views.xml",
        "views/budget_appropriation_master_summary_views.xml",
        "views/menu.xml",
    ],
    "auto_install": False,
    "application": False,
    "installable": True,
    "license": "AGPL-3",
}
