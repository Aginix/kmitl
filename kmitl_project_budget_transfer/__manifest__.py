{
    "name": "KMITL Project Budget Transfer",
    "version": "16.0.1.0.0",
    "summary": """ Filter the transfer-line project picker by dimensions, open
    supported projects to other units and show a project's Funding Summary """,
    "category": "KMITL/Budgeting",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "depends": [
        "kmitl_project",
        "budget_transfer",
    ],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "views/budget_transfer_views.xml",
        "views/kmitl_project_funding_views.xml",
        "views/kmitl_project_views.xml",
    ],
    # Auto-install wherever a budget transfer can fund a kmitl.project.
    "auto_install": True,
    "application": False,
    "license": "AGPL-3",
}
