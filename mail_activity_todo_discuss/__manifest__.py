{
    "name": "Mail Activity Todo - Discuss Panel",
    "version": "16.0.1.0.0",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "Productivity",
    "summary": "Show your Todo inbox inside Discuss, next to your messages",
    "description": """
Surfaces the unified Todo inbox (from mail_activity_todo) as a panel in the
Discuss sidebar, so every piece of incoming work addressed to the user — chat
messages, mailbox notifications and actionable Todos — lives in one place.

The panel lists pending Todos grouped by source app with live counts, opens a
filtered Todo list on click, and offers a "View all" link straight to the Todo
app.
""",
    "depends": [
        "mail_activity_todo",
    ],
    "data": [],
    "assets": {
        "web.assets_backend": [
            "mail_activity_todo_discuss/static/src/js/discuss_todo_panel.esm.js",
            "mail_activity_todo_discuss/static/src/scss/discuss_todo_panel.scss",
            "mail_activity_todo_discuss/static/src/xml/discuss_todo_panel.xml",
        ],
    },
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
