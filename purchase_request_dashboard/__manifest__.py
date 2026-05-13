{
    "name": "Purchase Request Dashboard",
    "version": "16.0.1.0.0",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "KMITL",
    "depends": [
        "web",
        "purchase_request_leadtime",
        "purchase_request_verify_state",
        "purchase_request_budget",
    ],
    "data": [
        "views/purchase_request_dashboard_menus.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "purchase_request_dashboard/static/src/components/**/*",
        ],
    },
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
