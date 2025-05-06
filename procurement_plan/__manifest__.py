# -*- coding: utf-8 -*-
{
    "name": "Procurement Plan",
    "version": "16.0.1.0.0",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "KMITL",
    "depends": ["base", "account_fiscal_year", "l10n_th_kmitl_procurement"],
    "data": [
        "security/ir.model.access.csv",
        "views/procurement_plan_views.xml"
        "views/procurement_plan_menus.xml",
    ],
    "application": False,
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
