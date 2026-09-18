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

A collapsible "Todos" section in the Discuss sidebar (next to
Inbox/Starred/History) lists pending Todos grouped by source app with live
counts. Clicking the header opens the full Todo page in the main content pane;
clicking an app group opens it filtered to that app. A "History" entry below the
groups opens the already-handled Todos (dismissed with Mark as Read plus
completed ones) in the same pane. The page lists each Todo
with its detail (app, source record, activity type, assignee, note, who created
it and when — as a relative time — and a colour-coded deadline countdown), each
clickable straight to its source document, plus a link to the full Todo app. A
search box filters the list and a toggle groups it by activity type into
collapsible sections (so a crowded inbox can be focused one type at a time); the
grouping choice is remembered across sessions. The activity systray routes here
too, opening the page filtered to the clicked app.
""",
    "depends": [
        "mail_activity_todo",
    ],
    "data": [],
    "assets": {
        "web.assets_backend": [
            "mail_activity_todo_discuss/static/src/models/discuss.esm.js",
            "mail_activity_todo_discuss/static/src/js/discuss_todo_view.esm.js",
            "mail_activity_todo_discuss/static/src/js/discuss_todo_sidebar.esm.js",
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
