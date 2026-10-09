{
    "name": "KMITL Project Funding",
    "version": "16.0.1.0.0",
    "summary": "Funding Summary (เงินสนับสนุนที่ได้รับ) of a project, readable without budget rights",
    "category": "KMITL/Budgeting",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "depends": [
        "kmitl_project_budget_transfer",
    ],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "views/kmitl_project_funding_views.xml",
        "views/kmitl_project_views.xml",
    ],
    # Auto-install wherever budget transfers meet kmitl.project.
    "auto_install": True,
    "application": False,
    "license": "AGPL-3",
}
