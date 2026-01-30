{
    "name": "Account Move Request Budget",
    "version": "16.0.1.0.0",
    "category": "KMITL/Budgeting",
    "license": "AGPL-3",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "depends": [
        "account_move_request",
        "account_move_request_fiscal_year",
        "budget",
        "base_fontawesome"
    ],
    "data": [
        "views/account_move_request_views.xml",
        "views/budget_commitment_views.xml",
        "report/report_account_move_request_inherited.xml",
    ],
    "auto_install": False,
    "application": False,
    "installable": True,
}
