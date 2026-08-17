{
    "name": "KMITL Budget Transfer",
    "version": "16.0.1.0.0",
    "summary": """ Budget transfer (การโอนงบประมาณ) split out of the budget core """,
    "category": "KMITL/Budgeting",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "depends": [
        "budget",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/budget_transfer_sequence.xml",
        "views/budget_move_views.xml",
        "views/budget_transfer_views.xml",
        "views/budget_transfer_menus.xml",
    ],
    # Auto-install wherever `budget` is present: this keeps the transfer feature
    # available on every environment that already runs the core module (incl.
    # production) and guarantees the ir_model_data ownership hand-over in
    # budget's 16.0.2.0.0 pre-migration runs in the same upgrade pass. See
    # budget ADR-0013.
    "auto_install": True,
    "application": False,
    "license": "AGPL-3",
}
