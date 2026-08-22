# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name": "Web Richtext Style",
    "category": "Technical",
    "version": "16.0.1.0.0",
    "author": "Aginix Technologies",
    "website": "https://github.com/Aginix/kmitl",
    "summary": "Add custom toolbar options to the HTML richtext editor",
    "depends": ["web_editor"],
    "auto_install": False,
    "installable": True,
    "assets": {
        "web.assets_backend": [
            "web_richtext_style/static/src/js/wysiwyg_patch.js",
            "web_richtext_style/static/src/js/html_field_patch.js",
        ],
    },
    "license": "LGPL-3",
}
