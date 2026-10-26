{
    "name": "KMITL Project Budget Overview",
    "version": "16.0.1.0.0",
    "summary": "บัญชีโครงการ — one page for a project's budget figures, "
    "movements and money actions",
    "category": "KMITL/Budgeting",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "depends": ["kmitl_project_budget_movement"],
    "data": ["views/kmitl_project_views.xml"],
    "assets": {
        "web.assets_backend": [
            "kmitl_project_budget_overview/static/src/budget_overview/*",
        ],
    },
    # Replaces the movement / commitment stat buttons wherever they exist.
    "auto_install": True,
    "application": False,
    "license": "AGPL-3",
}
