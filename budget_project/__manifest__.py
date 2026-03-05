{
    "name": "Budget Project",
    "version": "16.0.1.0.0",
    "category": "KMITL/Budget",
    "summary": "Budget management for projects and activities",
    "description": """
Budget Project Management
=========================

This module adds project/activity budgeting capabilities to the budget system.

Features:
---------
* Create and manage budget projects/activities
* Link projects to specific budget accounts
* Integrate with budget appropriation for project allocation
    """,
    "author": "KMITL",
    "website": "https://www.kmitl.ac.th",
    "depends": [
        "budget",
        "account_analytic_kmitl",
        "kmitl_project"
    ],
    "data": [
        "data/budget_account_project_update.xml",
        "views/budget_account_views.xml",
    ],
    "installable": True,
    "auto_install": False,
    "application": False,
    "license": "LGPL-3",
}
