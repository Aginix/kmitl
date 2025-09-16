{
    "name": "Account Payment Budget",
    "version": "16.0.1.0.0",
    "summary": "Budget integration for account payments",
    "description": """
Account Payment Budget
======================

This module provides integration between Odoo's account payment system
and KMITL's budget management system.

Key Features:
-------------
* Budget integration for payment processing
* Budget availability validation for payments
* Integration with KMITL's 4-dimensional financial tracking
* Budget commitment workflow for payments

Business Purpose:
-----------------
This module ensures that payment processing is properly integrated with
budget controls and financial tracking requirements.
    """,
    "category": "KMITL/Budgeting",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "depends": [
        "account",
        "budget"
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/account_payment_views.xml",
    ],
    "auto_install": False,
    "application": False,
    "installable": True,
    "license": "AGPL-3",
}
