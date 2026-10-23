{
    "name": "KMITL Account Analytic",
    "version": "16.0.1.2.2",
    "summary": """ KMITL Account Analytic""",
    "category": "KMITL/Accounting",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "depends": [
        "account_analytic_parent",
        "account_analytic_plan_code",
        "account_analytic_seq",
    ],
    "data": [
        "data/account.analytic.plan.xml",
        "data/account.analytic.account.xml",
        "views/account_analytic_account_views.xml",
    ],
    "auto_install": False,
    "license": "AGPL-3",
}
