{
    "name": "Account Expense Request Demo",
    "version": "16.0.1.0.0",
    "category": "Accounting",
    "license": "LGPL-3",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "depends": ["budget", "account_expense_request", "base_tier_validation"],
    "data": [
        "security/ir.model.access.csv",
        "data/sequence.xml",
        "data/tier_definition.xml",
        "views/account_expense_request_demo_view.xml",
    ],
    "installable": True,
    "application": False,
}
