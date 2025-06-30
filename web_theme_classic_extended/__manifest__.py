{
    "name": "Web Theme Classic Extended",
    "version": "16.0.1.0.0",
    "summary": """ Web Theme Classic Extended Summary """,
    "author": "Aginix Technologies",
    "website": "https://github.com/Aginix/kmitl",
    "category": "Extra Tools",
    "depends": ["web", "web_theme_classic"],
    "assets": {
        "web.assets_backend": [
            (
                "replace",
                "/web_theme_classic/static/src/scss/web_theme_classic.scss",
                "/web_theme_classic_extended/static/src/scss/web_theme_classic.scss",
            ),
        ],
    },
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
