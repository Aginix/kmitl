{
    "name": "Purchase Request Dashboard — Budget",
    "version": "16.0.1.0.0",
    "summary": "Expense-category charts (by budget_account_id) for the Purchase Request dashboard",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "KMITL",
    "depends": [
        "purchase_request_dashboard",
        "purchase_request_budget",
    ],
    "assets": {
        "web.assets_backend": [
            "purchase_request_dashboard_budget/static/src/**/*",
        ],
    },
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
