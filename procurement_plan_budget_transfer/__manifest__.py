{
    "name": "Procurement Plan Budget Transfer",
    "version": "16.0.1.1.1",
    "summary": "จองงบประมาณแผนจัดซื้อจัดจ้างอัตโนมัติเมื่อโอนงบเข้าครบตามแผน",
    "author": "Aginix Technologies",
    "website": "https://github.com/Aginix/kmitl",
    "category": "KMITL/Budgeting",
    "depends": [
        "procurement_plan_budget",
        "budget_transfer",
    ],
    "data": [
        "views/budget_transfer_views.xml",
    ],
    "installable": True,
    # Auto-install wherever a budget transfer can fund a procurement plan.
    "auto_install": True,
    "license": "LGPL-3",
}
