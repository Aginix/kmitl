# -*- coding: utf-8 -*-
{
    "name": "Budget Transfer Procurement Plan",
    "version": "16.0.1.0.0",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "KMITL",
    "summary": "Extend budget transfers to support procurement plan analytics",
    "description": """
Budget Transfer Procurement Plan
================================

This module extends the budget transfer functionality to support 
procurement plan analytic tracking. It allows budget transfers 
to be associated with specific procurement plans through the
procurement_plan_analytic_id field.

Key Features:
- Add procurement plan analytic field to budget transfers
- Include procurement plan data in budget validation
- Extend budget move creation with procurement plan analytics
- Maintain full audit trail for procurement-related transfers

This module follows the same pattern as procurement_plan_budget
for consistent analytic dimension handling across the system.
    """,
    "depends": [
        "budget",
        "procurement_plan_analytic",
    ],
    "data": [
        "views/budget_transfer_views.xml",
    ],
    "application": False,
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}