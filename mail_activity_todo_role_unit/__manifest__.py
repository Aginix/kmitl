{
    "name": "Mail Activity Todo: Role-in-Unit Routing",
    "version": "16.0.1.0.0",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "Productivity",
    "summary": "Route group Todos to holders of a role within an operating unit, "
    "resolved live (ADR-0002)",
    "depends": [
        "mail_activity_todo",
        "base_user_role",
        "operating_unit",
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
