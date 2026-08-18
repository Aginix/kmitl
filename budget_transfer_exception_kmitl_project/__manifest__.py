{
    "name": "KMITL Budget Transfer Exception: Project",
    "version": "16.0.1.0.0",
    "summary": """ Check project (is_project) transfer lines against their kmitl.project source """,
    "category": "KMITL/Budgeting",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "depends": [
        "budget_transfer_exception",
        "kmitl_project",
    ],
    "data": [
        "data/exception_rule_data.xml",
    ],
    # Auto-install wherever the transfer-exception framework meets kmitl.project.
    "auto_install": True,
    "application": False,
    "license": "AGPL-3",
}
