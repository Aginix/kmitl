{
    "name": "Account Expense Request Compensation",
    "version": "16.0.1.0.0",
    "category": "Accounting",
    "license": "LGPL-3",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "depends": ["account_expense_request"],
    "data": [
        "security/ir.model.access.csv",
        "data/sequence.xml",
        "views/account_expense_request_compensation_view.xml",
        "views/account_expense_request_compensation_type_view.xml",
    ],
    "installable": True,
    "application": False,
}
