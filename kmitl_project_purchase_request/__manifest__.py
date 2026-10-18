{
    "name": "KMITL Project Purchase Request",
    "version": "16.0.1.3.0",
    "category": "KMITL",
    "summary": "Buy a purchase request (พ.1) under a KMITL project's reserved budget",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "depends": ["kmitl_project", "purchase_request_budget", "purchase"],
    "data": [
        "security/ir.model.access.csv",
        "security/security.xml",
        "views/purchase_request_views.xml",
        "views/kmitl_project_views.xml",
    ],
    "application": False,
    "installable": True,
    # Glue module: activate automatically whenever both sides are present, so the
    # "standalone PR may not use a project budget code" rule (ADR-0007) is always
    # enforced when projects and budget-aware purchase requests coexist.
    "auto_install": True,
    "license": "LGPL-3",
}
