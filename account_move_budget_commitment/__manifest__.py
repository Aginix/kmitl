{
    "name": "Account Move Budget Commitment",
    "version": "16.0.1.0.0",
    "summary": "Budget commitment integration for account moves",
    "description": """
Account Move Budget Commitment
===============================

This module provides integration between Odoo's standard account moves (journal entries)
and KMITL's budget system, enabling automatic budget consumption and validation.

Key Features:
-------------
* Automatic budget consumption when posting account moves
* Budget availability checking before posting
* Integration with KMITL's 4-dimensional financial tracking
* Support for budget commitment workflow
* Budget vs actual reporting integration

Business Purpose:
-----------------
This module ensures that all accounting transactions are properly tracked against
budgets, providing real-time budget consumption monitoring and preventing
over-expenditure through budget availability validation.

Technical Implementation:
-------------------------
* Extends account.move model with budget integration
* Automatic budget.move creation for consumption tracking  
* Links account moves to budget accounts via analytic dimensions
* Integrates with existing budget approval workflows
    """,
    "category": "KMITL/Budgeting",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "depends": [
        "account",
        "budget",
        "account_analytic_kmitl",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/account_move_views.xml",
        "data/budget_journal_config.xml",
    ],
    "auto_install": False,
    "application": False,
    "installable": True,
    "license": "AGPL-3",
}