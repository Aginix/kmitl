{
    "name": "KMITL Project Budget Transfer",
    "version": "16.0.2.0.0",
    "summary": """ Filter the transfer-line project picker by dimensions, open
    supported projects to other units, and move floating budget into a project
    (จัดสรรงบประมาณ (งบลอย)) and back out (โอนคืนงบลอย) """,
    "category": "KMITL/Budgeting",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "depends": [
        "kmitl_project",
        "budget_transfer",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/budget_transfer_views.xml",
        "views/kmitl_project_views.xml",
        "wizard/kmitl_project_floating_allocation_views.xml",
        "wizard/kmitl_project_floating_return_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "kmitl_project_budget_transfer/static/src/floating_allocation/*",
        ],
    },
    # Auto-install wherever a budget transfer can fund a kmitl.project.
    "auto_install": True,
    "application": False,
    "license": "AGPL-3",
}
