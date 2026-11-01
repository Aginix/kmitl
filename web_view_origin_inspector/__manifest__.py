{
    "name": "Web View Origin Inspector",
    "version": "16.0.1.0.0",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "Hidden/Tools",
    "summary": "Debug mode: click a button or field to see which views declare "
    "and modify it, hide it, and log manual view changes for porting to code",
    "depends": [
        "web",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/ir_ui_view_change_log_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "web_view_origin_inspector/static/src/js/view_origin_inspector.esm.js",
            "web_view_origin_inspector/static/src/xml/view_origin_inspector.xml",
            "web_view_origin_inspector/static/src/scss/view_origin_inspector.scss",
        ],
    },
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
