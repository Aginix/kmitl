{
    "name": "Procurement Plan Budget Overview",
    "version": "16.0.1.0.0",
    "summary": "บัญชีแผน — one page for a procurement plan's budget figures, "
    "movements and money actions",
    "category": "KMITL/Budgeting",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "depends": ["procurement_plan_budget_movement"],
    "data": ["views/procurement_plan_views.xml"],
    "assets": {
        "web.assets_backend": [
            "procurement_plan_budget_overview/static/src/budget_overview/*",
        ],
    },
    # Replaces the movement / commitment stat buttons wherever they exist.
    "auto_install": True,
    "application": False,
    "license": "LGPL-3",
}
