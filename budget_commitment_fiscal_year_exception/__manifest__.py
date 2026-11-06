{
    "name": "Budget Commitment: Current Fiscal Year Exception",
    "version": "16.0.1.0.0",
    "summary": """ Block reserving (จองงบ) a budget commitment unless its ปีงบประมาณ is the current one """,
    "category": "KMITL/Budgeting",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "depends": [
        "budget",
        "base_exception",
    ],
    "data": [
        "data/exception_rule_data.xml",
    ],
    "auto_install": False,
    "application": False,
    "license": "AGPL-3",
}
