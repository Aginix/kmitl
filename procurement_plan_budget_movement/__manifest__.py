{
    "name": "Procurement Plan Budget Movement",
    "version": "16.0.1.0.0",
    "summary": "Plan Budget Movements (การเคลื่อนไหวงบ), readable by plan users "
    "without budget rights",
    "category": "KMITL/Budgeting",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "depends": [
        "procurement_plan_budget_transfer",
        "procurement_plan_operating_unit_access_all",
    ],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "views/procurement_plan_budget_move_line_views.xml",
        "views/procurement_plan_views.xml",
    ],
    # Auto-install wherever plans meet budget transfers and operating units.
    "auto_install": True,
    "application": False,
    "license": "LGPL-3",
}
