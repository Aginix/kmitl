{
    "name": "KMITL Budget Commitment Exception",
    "version": "16.0.1.0.0",
    "summary": """ base.exception framework checked when a budget commitment is reserved """,
    "category": "KMITL/Budgeting",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "depends": [
        "budget",
        "base_exception",
    ],
    "data": [
        "views/budget_commitment_views.xml",
    ],
    # Rules live in thin bridge modules (e.g.
    # budget_commitment_exception_procurement_plan).
    "auto_install": True,
    "application": False,
    "license": "AGPL-3",
}
