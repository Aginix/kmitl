{
    "name": "Tier Validation Todo Bridge",
    "version": "16.0.1.0.0",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "Productivity",
    "summary": "Suppress the OCA tier_validation ReviewerMenu so the unified "
    "mail_activity_todo bell is the single inbox.",
    "depends": [
        "mail_activity_todo",
        "base_tier_validation",
    ],
    "data": [],
    "assets": {
        "web.assets_backend": [
            "base_tier_validation_todo/static/src/js/hide_tier_validation_systray.esm.js",
        ],
    },
    "installable": True,
    "auto_install": True,
    "license": "LGPL-3",
}
