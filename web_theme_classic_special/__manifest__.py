{
    "name": "Web_theme_classic_special",
    "version": "16.0.1.0.0",
    "summary": """ Web_theme_classic_special Summary """,
    "author": "Aginix",
    "website": "https://github.com/Aginix/kmitl",
    "category": "Extra Tools",
    "depends": ["web", "web_theme_classic"],
    "assets": {
        "web.assets_backend": [
            (
                "replace",
                "/web_theme_classic/static/src/scss/web_theme_classic.scss",
                "/web_theme_classic_special/static/src/scss/web_theme_classic.scss",
            ),
        ],
    },
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
