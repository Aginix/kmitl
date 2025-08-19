{
    "name": "KMITL Budget Appropriation Demo",
    "version": "16.0.1.0.1",
    "summary": "Demo data for KMITL Budget Appropriation system",
    "category": "KMITL/Budgeting",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "depends": ["account_analytic_kmitl", "budget_appropriation", "kmitl_demo"],
    "data": [
        "data/budget.appropriation.csv",
        "data/budget.appropriation.line.csv",
    ],
    "post_init_hook": "post_init_hook",
    "post_load_hook": "post_load_hook",
    "uninstall_hook": "uninstall_hook",
    "auto_install": False,
    "application": True,
    "license": "AGPL-3",
}
