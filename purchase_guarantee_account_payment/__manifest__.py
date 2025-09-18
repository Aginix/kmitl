{
    "name": "Purchase Guarantee Account Payment",
    "version": "16.0.1.0.0",
    "summary": "Purchase Guarantee Account Payment Management",
    "description": """
Purchase Guarantee Account Payment
==================================

This module provides account payment integration for purchase guarantee management.

Key Features:
-------------
* Guarantee payment classification and tracking
* Integration with existing purchase.guarantee.method from l10n_th_gov_purchase_guarantee
* Automatic account assignment based on purchase guarantee method
* Enhanced payment workflow for guarantee transactions

Business Purpose:
-----------------
This module enables automatic account assignment for guarantee-related payments based 
on purchase guarantee methods. It provides seamless integration between payment 
processing and existing purchase guarantee workflows.

Technical Implementation:
-------------------------
* Extended account.payment model with guarantee payment fields
* Integration with purchase.guarantee.method model from l10n_th_gov_purchase_guarantee
* Automatic account selection in payment journal entries based on guarantee method
* Leverages existing purchase guarantee infrastructure
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
        "views/account_payment_views.xml",
    ],
    "auto_install": False,
    "application": False,
    "installable": True,
    "license": "AGPL-3",
}
