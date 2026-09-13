# -*- coding: utf-8 -*-
{
    "name": "Web Notebook Invalid Field Indicator",
    "summary": "Highlight notebook tabs in red when they contain invalid fields after save fail",
    "version": "16.0.1.0.0",
    "author": "KMITL",
    "website": "https://github.com/aginix/kmitl",
    "category": "Web",
    "depends": ["web"],
    "data": [],
    "assets": {
        "web.assets_backend": [
            "web_notebook_invalid_indicator/static/src/form_compiler_patch.js",
            "web_notebook_invalid_indicator/static/src/notebook_invalid.scss",
        ],
    },
    "application": False,
    "installable": True,
    "auto_install": True,
    "license": "LGPL-3",
}
