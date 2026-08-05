{
    "name": "Mail Activity Todo — Notification Sound",
    "version": "16.0.1.0.0",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "Productivity",
    "summary": "Optional ding on a new Todo, with a per-user on/off toggle in Preferences",
    "depends": [
        "mail_activity_todo",
    ],
    "data": [
        "views/res_users_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "mail_activity_todo_sound/static/src/js/todo_sound_handler.esm.js",
        ],
    },
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
