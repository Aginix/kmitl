{
    "name": "Aginix Approval - Favorite Request Categories",
    "version": "16.0.1.0.0",
    "category": "KMITL",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "license": "LGPL-3",
    "depends": ["agx_approval_dashboard_tree"],
    "data": [
        "views/approval_category_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "agx_approval_dashboard_tree_favorite/static/src/views/category_tree_favorite.esm.js",
            "agx_approval_dashboard_tree_favorite/static/src/views/category_tree_favorite.xml",
            "agx_approval_dashboard_tree_favorite/static/src/views/category_tree_favorite.scss",
        ],
    },
    "installable": True,
    "auto_install": False,
}
