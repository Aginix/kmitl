{
    "name": "Purchase Request Dashboard — Leadtime",
    "version": "16.0.1.0.0",
    "summary": "State-transition leadtime treemap for the Purchase Request dashboard",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "KMITL",
    "depends": [
        "purchase_request_dashboard",
        "purchase_request_leadtime",
    ],
    "assets": {
        "web.assets_backend": [
            "purchase_request_dashboard_leadtime/static/src/**/*",
        ],
    },
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
