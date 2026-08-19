{
    "name": "Tier Validation — Hide Reviewer Menu Systray",
    "version": "16.0.1.0.0",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "Productivity",
    "summary": "Suppress the OCA tier_validation ReviewerMenu bell.",
    "depends": [
        "base_tier_validation",
    ],
    "data": [],
    "assets": {
        "web.assets_backend": [
            "base_tier_validation_hide_systray/static/src/js/hide_systray.esm.js",
        ],
    },
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
