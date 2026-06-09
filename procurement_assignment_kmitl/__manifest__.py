# -*- coding: utf-8 -*-
{
    "name": "Procurement Assignment KMITL",
    "version": "16.0.1.0.0",
    "summary": "Assign a responsible procurement officer to PR, PA and PO",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "KMITL",
    "depends": [
        "purchase_order_kmitl",
        "purchase_request_approval",
    ],
    "data": [
        "security/ir.model.access.csv",
        "wizards/assign_officer_wizard_views.xml",
        "views/purchase_request_views.xml",
        "views/purchase_order_views.xml",
        "views/purchase_request_approval_views.xml",
        "views/res_config_settings_views.xml",
    ],
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
