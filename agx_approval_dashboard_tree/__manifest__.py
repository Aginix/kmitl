{
    "name": "Aginix Approval - New Request Tree Dashboard",
    "version": "16.0.1.0.0",
    "category": "Accounting",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "license": "LGPL-3",
    "depends": ["agx_approval"],
    "data": [
        "views/approval_dashboard_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "agx_approval_dashboard_tree/static/src/views/category_tree.esm.js",
            "agx_approval_dashboard_tree/static/src/views/category_tree.xml",
            "agx_approval_dashboard_tree/static/src/views/category_tree.scss",
        ],
    },
    "installable": True,
    "auto_install": False,
}
