{
    "name": "KMITL Project Floating Allocation",
    "version": "16.0.1.0.0",
    "summary": """ จัดสรรงบประมาณ (งบลอย): move the floating budget covering a project's
    coordinate onto the project at once, without the transfer approval """,
    "category": "KMITL/Budgeting",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "depends": [
        "kmitl_project_budget_transfer",
    ],
    "data": [
        "security/ir.model.access.csv",
        "wizard/kmitl_project_floating_allocation_views.xml",
        "views/kmitl_project_views.xml",
        "views/budget_transfer_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "kmitl_project_floating_allocation/static/src/floating_allocation/*",
        ],
    },
    "application": False,
    "license": "AGPL-3",
}
