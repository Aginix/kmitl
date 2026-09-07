{
    "name": "Purchase Request Todos",
    "version": "16.0.1.0.0",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "KMITL",
    "summary": "Activity type definitions for the พ.1 / พจ.1 Todo lifecycle, "
    "and PA (พจ.1) workflow Todos (status FYI, manager consideration, "
    "record contract, PO creation)",
    "depends": [
        "base_automation",
        "mail_activity_todo_role_unit",
        "purchase_request_approval",
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
