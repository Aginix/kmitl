{
    "name": "Purchase Request Todos",
    "version": "16.0.1.0.0",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "KMITL",
    "summary": "Surface purchase-request approval/creation tasks (UC2) and notify "
    "the requester on status changes (UC3) in the unified inbox",
    "depends": [
        "mail_activity_todo",
        "purchase_request_approval",
        "purchase_request_activity_kmitl",
    ],
    "data": [
        "data/mail_activity_type.xml",
        "data/mail_activity_type_update.xml",
    ],
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
