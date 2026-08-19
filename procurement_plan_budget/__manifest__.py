# -*- coding: utf-8 -*-
{
    "name": "Procurement Plan Budget",
    "version": "16.0.1.1.0",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "KMITL",
    "depends": ["procurement_plan", "budget"],
    "data": [
        "data/budget_account_procurement_update.xml",
        "security/security.xml",
        "views/budget_account_views.xml",
        "views/budget_commitment_views.xml",
        "views/budget_move_views.xml",
        "views/procurement_plan_views.xml",
        "views/procurement_plan_menus.xml",
    ],
    "application": False,
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
