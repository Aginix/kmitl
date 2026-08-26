{
    "name": "Purchase Request Sarabun Todo",
    "version": "16.0.1.0.0",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "KMITL",
    "summary": "Route Sarabun signing Todos (endorsement letter, signer, endorsement approved) "
    "for the พ.1 lifecycle",
    "depends": [
        "base_automation",
        "purchase_request_todo",
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
