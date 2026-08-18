{
    "name": "KMITL Budget Transfer Exception: Procurement Plan",
    "version": "16.0.1.0.0",
    "summary": """ Check procurement-plan transfer lines against their procurement.plan source """,
    "category": "KMITL/Budgeting",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "depends": [
        "budget_transfer_exception",
        "procurement_plan",
    ],
    "data": [
        "data/exception_rule_data.xml",
    ],
    # Auto-install wherever the transfer-exception framework meets procurement.plan.
    "auto_install": True,
    "application": False,
    "license": "AGPL-3",
}
