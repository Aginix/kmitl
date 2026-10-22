{
    "name": "Account Analytic Distribution Tree Selection (ztree)",
    "version": "16.0.1.0.0",
    "summary": "Browse hierarchical analytic dimensions as an expandable "
    "tree in the analytic distribution widget",
    "category": "KMITL/Accounting",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "depends": [
        "account_analytic_kmitl",
        "app_web_widget_ztree",
    ],
    "data": [
        "views/account_analytic_plan_views.xml",
        "data/account_analytic_plan_data.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "account_analytic_distribution_ztree/static/src/**/*",
        ],
    },
    "installable": True,
    "auto_install": False,
    "license": "AGPL-3",
}
