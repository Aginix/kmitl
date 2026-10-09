{
    "name": "KMITL Project Budget Movement",
    "version": "16.0.1.0.0",
    "summary": "Project Budget Movements (การเคลื่อนไหวงบประมาณโครงการ), "
    "readable by project owners without budget rights",
    "category": "KMITL/Budgeting",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "depends": [
        "kmitl_project_budget_transfer",
        "kmitl_project_coordinator",
    ],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "views/kmitl_project_budget_move_line_views.xml",
        "views/kmitl_project_views.xml",
    ],
    # Auto-install wherever budget transfers and project coordinators meet.
    "auto_install": True,
    "application": False,
    "license": "AGPL-3",
}
