{
    "name": "Purchase Request Dashboard",
    "version": "16.0.2.0.0",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "KMITL",
    "depends": [
        "web",
        "purchase_request_kmitl",
    ],
    "data": [
        "views/purchase_request_dashboard_menus.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "purchase_request_dashboard/static/src/**/*",
        ],
    },
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
