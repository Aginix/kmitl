{
    "name": "Account Payment Guarantee",
    "version": "16.0.1.0.0",
    "summary": "Account Payment Guarantee Management",
    "description": """
Account Payment Guarantee
=========================

This module provides guarantee management for account payments.

Key Features:
-------------
* Guarantee type classification for payments
* Account assignment based on guarantee type  
* Integration with purchase guarantee workflow
* Enhanced payment workflow for guarantee transactions
* Configurable guarantee types with custom accounts

Business Purpose:
-----------------
This module enables automatic account assignment for guarantee-related payments based 
on configurable guarantee types. It provides seamless integration between payment 
processing and guarantee management workflows.

Technical Implementation:
-------------------------
* Extended account.payment model with guarantee fields
* Configurable guarantee types with account assignment
* Automatic account selection in payment journal entries
* Integration with existing guarantee modules
    """,
    "category": "Accounting/Payments",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "depends": [
        "account",
        "l10n_th_gov_purchase_guarantee",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/account_payment_guarantee_type_views.xml",
        "views/account_payment_menus.xml",
        "views/account_payment_views.xml",
    ],
    "auto_install": False,
    "application": False,
    "installable": True,
    "license": "AGPL-3",
}