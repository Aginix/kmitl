{
    "name": "Mail Activity Todo: Per-User Notification Scope",
    "version": "16.0.1.0.0",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "Productivity",
    "summary": "Let users narrow group-Todo notifications by OU + activity type "
    "(ADR-0007). Splits notification scope from view scope so wide-access "
    "managers are not flooded by every OU's group Todos.",
    "depends": [
        "mail_activity_todo_role_unit",
    ],
    "data": [
        "security/ir.model.access.csv",
        "security/security.xml",
        "views/res_users_views.xml",
        "views/mail_activity_views.xml",
    ],
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
