# -*- coding: utf-8 -*-
{
    "name": "Procurement Plan Role",
    "version": "16.0.1.0.0",
    "summary": """ Grant procurement plan access to the budget planning roles """,
    "author": "Aginix Technologies",
    "website": "https://github.com/Aginix/kmitl",
    "category": "KMITL/Budgeting",
    "depends": [
        "budget_role",
        "procurement_plan",
    ],
    "data": [
        "security/res_users_role.xml",
    ],
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
