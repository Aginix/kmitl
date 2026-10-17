{
    "name": "Web Widget X2many Flow Diagram",
    "summary": "Show a one2many as a flow diagram of layered cards, "
    "with drag & drop reorder",
    "version": "16.0.1.0.0",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "development_status": "Beta",
    "category": "Hidden",
    "depends": ["web"],
    "assets": {
        "web.assets_backend": [
            "web_widget_x2many_flow/static/src/**/*",
        ],
        "web.qunit_suite_tests": [
            "web_widget_x2many_flow/static/tests/**/*",
        ],
    },
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
