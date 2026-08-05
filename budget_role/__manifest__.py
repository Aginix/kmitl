# -*- coding: utf-8 -*-
{
    "name": "Budget Role",
    "version": "16.0.1.0.0",
    "summary": """ Predefined user roles for the budget planning workflow """,
    "author": "Aginix Technologies",
    "website": "https://github.com/Aginix/kmitl",
    "category": "KMITL/Budgeting",
    "depends": [
        "budget",
        "base_user_role",
        "budget_operating_unit",
        "budget_operating_unit_access_all",
        "account",
        "analytic_operating_unit_access_all",
    ],
    "data": [
        "security/res_users_role.xml",
    ],
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
