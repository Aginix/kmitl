{
    "name": "Web Richtext Sticky Toolbar",
    "category": "Technical",
    "version": "16.0.1.0.0",
    "author": "Aginix Technologies",
    "website": "https://github.com/Aginix/kmitl",
    "summary": "Always-visible toolbar pinned at the top of the HTML richtext field",
    "depends": ["web_editor"],
    "auto_install": False,
    "installable": True,
    "assets": {
        "web.assets_backend": [
            "web_richtext_sticky_toolbar/static/src/js/wysiwyg_patch.js",
            "web_richtext_sticky_toolbar/static/src/js/html_field_patch.js",
            "web_richtext_sticky_toolbar/static/src/scss/sticky_toolbar.scss",
        ],
    },
    "license": "LGPL-3",
}
