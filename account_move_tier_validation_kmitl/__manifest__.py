{
    "name": "Account Move Tier Validation KMITL",
    "version": "16.0.1.0.0",
    "category": "KMITL/Accounting",
    "summary": "KMITL integration for Account Move Tier Validation",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "license": "AGPL-3",
    "depends": [
        "account_move_tier_validation",
        "account_move_submitted_state",
    ],
    "data": [
        "views/account_move_views.xml",
        "data/tier_definition.xml",
    ],
    "installable": True,
    "auto_install": False,
    "application": False,
}
