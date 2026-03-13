{
    "name": "Account Move KMITL",
    "version": "16.0.1.0.0",
    "category": "KMITL/Accounting",
    "summary": "KMITL customizations for Account Moves: submitted state, "
    "tier validation, and budget commitment linking",
    "author": "KMITL",
    "website": "https://www.kmitl.ac.th",
    "license": "AGPL-3",
    "depends": [
        "account_move_tier_validation",
        "budget",
    ],
    "data": [
        "views/account_move_views.xml",
        "data/tier_definition.xml",
    ],
    "installable": True,
    "auto_install": False,
    "application": False,
}
