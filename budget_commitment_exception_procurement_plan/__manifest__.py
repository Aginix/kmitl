{
    "name": "KMITL Budget Commitment Exception: Procurement Plan",
    "version": "16.0.1.0.0",
    "summary": """ A reservation on a procurement-plan budget code must name its plan """,
    "category": "KMITL/Budgeting",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "depends": [
        "budget_commitment_exception",
        "procurement_plan_budget",
    ],
    "data": [
        "data/exception_rule_data.xml",
    ],
    "auto_install": True,
    "application": False,
    "license": "AGPL-3",
}
