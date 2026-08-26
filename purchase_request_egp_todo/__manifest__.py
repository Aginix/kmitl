{
    "name": "Purchase Request E-GP Todo",
    "version": "16.0.1.0.0",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "KMITL",
    "summary": "Route E-GP number entry Todos for พ.1 in the e-GP procurement path",
    "depends": [
        "base_automation",
        "purchase_request_egp",
        "purchase_request_sarabun",
        "mail_activity_todo_role_unit",
        "purchase_user_role",
    ],
    "data": [
        "data/mail_activity_type.xml",
        "data/base_automation.xml",
    ],
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
