{
    "name": "Purchase Request Dashboard — e-GP",
    "version": "16.0.1.0.0",
    "summary": "Adds the in_egp state summary box to the Purchase Request dashboard",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "KMITL",
    "depends": [
        "purchase_request_dashboard",
        "purchase_request_egp",
    ],
    "assets": {
        "web.assets_backend": [
            "purchase_request_dashboard_egp/static/src/**/*",
        ],
    },
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
