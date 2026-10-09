{
    "name": "KMITL Budget Ledger",
    "version": "16.0.1.0.0",
    "summary": """ Post every commitment event to the budget ledger so
    budget.move.line is the one source of budget figures """,
    "category": "KMITL/Budgeting",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "depends": [
        "budget",
        "budget_transfer",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/budget_move_views.xml",
        "views/budget_commitment_views.xml",
        "views/budget_ledger_reconcile_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "budget_ledger/static/src/js/budget_ledger_drill.js",
        ],
    },
    "post_init_hook": "post_init_hook",
    # Every budget figure reads the ledger once this is installed (ADR-0016),
    # so it installs wherever the core budget + transfer modules run.
    "auto_install": True,
    "application": False,
    "license": "AGPL-3",
}
