{
    "name": "Mail Activity Todo - Discuss",
    "version": "16.0.1.0.0",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "Productivity",
    "summary": "Make Todos a first-class destination inside Discuss",
    "description": """
Surfaces the unified Todo inbox (from mail_activity_todo) inside Discuss, so
every piece of incoming work addressed to the user — chat messages, mailbox
notifications and actionable Todos — lives in one place.

A "Todos" row in the Discuss sidebar (next to Inbox/Starred/History) opens the
Todo inbox in the main content pane: the user's open Todos (up to 100), each
clickable straight to its source document, plus a link to the full Todo app.
The activity systray routes here too, so clicking it lands on the Todos page
in Discuss.
""",
    "depends": [
        "mail_activity_todo",
    ],
    "data": [],
    "assets": {
        "web.assets_backend": [
            "mail_activity_todo_discuss/static/src/models/discuss.esm.js",
            "mail_activity_todo_discuss/static/src/js/discuss_todo_view.esm.js",
            "mail_activity_todo_discuss/static/src/js/discuss_todo_sidebar_item.esm.js",
            "mail_activity_todo_discuss/static/src/js/todo_systray_patch.esm.js",
            "mail_activity_todo_discuss/static/src/scss/discuss_todo.scss",
            "mail_activity_todo_discuss/static/src/xml/discuss_todo_view.xml",
            "mail_activity_todo_discuss/static/src/xml/discuss_todo_sidebar.xml",
        ],
    },
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
