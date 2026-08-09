{
    "name": "Purchase Request Todos: Reserve Budget (พ.1)",
    "version": "16.0.1.0.0",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "KMITL",
    "summary": "Route a 'reserve budget' Todo to the จองงบประมาณ role of the "
    "purchase request's operating unit when it enters รอจองงบประมาณ",
    "depends": [
        "mail_activity_todo_role_unit",
        "purchase_request_approval_kmitl",
        "budget_role",
    ],
    "data": [
        "data/mail_activity_type.xml",
    ],
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
