{
    "name": "KMITL Project Budget Ledger",
    "version": "16.0.1.0.0",
    "summary": """ A transfer into a reserved project's coordinate tops its
    reservation up (replaces the cancel-and-re-reserve resync) """,
    "category": "KMITL/Budgeting",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "depends": [
        "kmitl_project",
        "budget_ledger",
    ],
    "data": [],
    # Must always ride with budget_ledger: otherwise the old resync would cancel
    # and re-reserve a reservation the ledger is topping up.
    "auto_install": True,
    "application": False,
    "license": "AGPL-3",
}
