{
    "name": "Mail Workflow Notification (Systray Feed)",
    "version": "16.0.1.0.0",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "Technical",
    "summary": "Systray notification feed for workflow state-change events, bypassing Discuss Inbox and the Todo system",
    "depends": [
        "mail",
    ],
    "data": [
        "views/res_users_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "mail_workflow_notification/static/src/js/workflow_notification_systray.esm.js",
            "mail_workflow_notification/static/src/js/workflow_notification_handler.esm.js",
            "mail_workflow_notification/static/src/scss/workflow_notification_systray.scss",
            "mail_workflow_notification/static/src/xml/workflow_notification_systray.xml",
        ],
    },
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
