# -*- coding: utf-8 -*-
{
    "name": "L10n_th_kmitl_procurement",
    "version": "",
    "summary": """ L10n_th_kmitl_procurement Summary """,
    "author": "",
    "website": "",
    "category": "",
    "depends": ["base", "hr", "purchase_request"],
    "data": [
        "security/ir.model.access.csv",
        "views/procurement_method_views.xml",
        "views/procurement_type_views.xml",
        "views/purchase_type_views.xml",
        "data/procurement_method.xml",
        "data/procurement_type.xml",
        "data/purchase_type.xml",
    ],
    "application": True,
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
