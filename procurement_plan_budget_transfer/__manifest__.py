# -*- coding: utf-8 -*-
{
    "name": "Procurement Plan Budget Transfer",
    "version": "16.0.1.0.0",
    "summary": "จองงบประมาณแผนจัดซื้อจัดจ้างอัตโนมัติเมื่อโอนงบเข้าครบตามแผน",
    "author": "Aginix Technologies",
    "website": "https://github.com/Aginix/kmitl",
    "category": "KMITL/Budgeting",
    "depends": [
        "procurement_plan_budget",
        "budget_transfer",
    ],
    "data": [],
    "installable": True,
    # Auto-install wherever a budget transfer can fund a procurement plan.
    "auto_install": True,
    "license": "LGPL-3",
}
