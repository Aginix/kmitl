{
    "name": "KMITL Project Purchase Order",
    "version": "16.0.1.0.0",
    "category": "KMITL",
    "summary": "Draw a standalone purchase order from a KMITL project's reserved budget",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "depends": ["purchase_budget", "kmitl_project_purchase_request"],
    "data": ["views/purchase_order_views.xml"],
    "application": False,
    "installable": True,
    # Glue module: a standalone PO may only reach a project's commitment through
    # the project picker, so activate whenever both sides are present.
    "auto_install": True,
    "license": "LGPL-3",
}
