{
    "name": "Purchase Request Todos",
    "version": "16.0.1.0.0",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "KMITL",
    "summary": "Surface purchase-request approval/creation tasks (UC2), notify "
    "the requester on status changes (UC3), and route the reserve-budget "
    "Todo to the จองงบประมาณ role of the พ.1's operating unit",
    "depends": [
        "mail_activity_todo_role_unit",
        "purchase_request_approval",
        "purchase_request_activity_kmitl",
        "purchase_request_approval_kmitl",
        "budget_role",
    ],
    "data": [
        "data/mail_activity_type.xml",
        "data/mail_activity_type_update.xml",
    ],
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
