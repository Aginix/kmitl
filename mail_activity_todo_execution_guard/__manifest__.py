{
    "name": "Mail Activity Todo — Execution Guard",
    "version": "16.0.1.0.0",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "Productivity",
    "summary": "Execution Todos cannot be marked done or cancelled by hand; "
    "they clear only by acting on the source document",
    "depends": [
        "mail_activity_todo",
    ],
    "data": [
        "views/mail_activity_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "mail_activity_todo_execution_guard/static/src/js/execution_guard.esm.js",
            "mail_activity_todo_execution_guard/static/src/xml/execution_guard.xml",
        ],
    },
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
