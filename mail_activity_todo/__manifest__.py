{
    "name": "Mail Activity Todo (Unified Action Inbox)",
    "version": "16.0.1.0.0",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "Productivity",
    "summary": "Unified inbox of pending work from every module, built on mail.activity",
    "depends": [
        "mail",
    ],
    "data": [
        "security/ir.model.access.csv",
        "security/security.xml",
        "data/ir_cron.xml",
        "views/mail_activity_views.xml",
        "views/todo_log_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "mail_activity_todo/static/src/js/todo_systray.esm.js",
            "mail_activity_todo/static/src/js/todo_notification_handler.esm.js",
            "mail_activity_todo/static/src/js/hide_native_activity_systray.esm.js",
            "mail_activity_todo/static/src/scss/todo_systray.scss",
            "mail_activity_todo/static/src/xml/todo_systray.xml",
        ],
    },
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
