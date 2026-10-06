{
    "name": "Budget Dashboard Pool Tag Items",
    "version": "16.0.1.0.0",
    "summary": "List projects / procurement plans under each budget code in "
    "the ตรวจสอบงบประมาณ report",
    "category": "KMITL/Budgeting",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "license": "LGPL-3",
    "depends": ["budget"],
    "assets": {
        "web.assets_backend": [
            "budget_dashboard_pool_tag/static/src/dashboard/budget_dashboard_pool_tag.esm.js",
            "budget_dashboard_pool_tag/static/src/dashboard/budget_dashboard_pool_tag.xml",
            "budget_dashboard_pool_tag/static/src/dashboard/budget_dashboard_pool_tag.scss",
        ],
    },
    "application": False,
    "installable": True,
    "auto_install": False,
}
