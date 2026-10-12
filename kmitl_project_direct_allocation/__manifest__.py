{
    "name": "KMITL Project Direct Allocation",
    "version": "16.0.1.0.0",
    "summary": """ จัดสรรจากเงินลอย: allocate a project from floating budget and
    reserve it in one step, without the transfer approval """,
    "category": "KMITL/Budgeting",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "depends": [
        "kmitl_project",
        "budget_transfer",
    ],
    "data": [
        "security/ir.model.access.csv",
        "wizard/kmitl_project_direct_allocation_view.xml",
        "views/kmitl_project_views.xml",
    ],
    # Not auto-installed: skipping the transfer approval is a policy choice
    # (ADR-0009) — installing this module is that choice.
    "application": False,
    "license": "AGPL-3",
}
