# -*- coding: utf-8 -*-
{
    "name": "Budget Widget Ztree",
    "version": "16.0.1.0.0",
    "category": "KMITL/Budgeting",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "depends": ["budget", "budget_transfer", "app_web_widget_ztree"],
    "data": [
        "views/budget_commitment_views.xml",
        "views/budget_transfer_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "budget_web_widget_ztree/static/src/js/budget_dashboard_ztree_patch.js",
            "budget_web_widget_ztree/static/src/js/budget_dashboard_ztree_patch.xml",
        ],
    },
    "application": False,
    "installable": True,
    "auto_install": False,
    "license": "AGPL-3",
}
