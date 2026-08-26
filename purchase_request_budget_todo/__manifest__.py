{
    "name": "Purchase Request Budget Todo",
    "version": "16.0.1.0.0",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "KMITL",
    "summary": "Route reserve-budget Todos when a พ.1 enters รอจองงบประมาณ",
    "depends": [
        "base_automation",
        "budget_role",
        "mail_activity_todo_role_unit",
    ],
    "data": [
        "data/mail_activity_type.xml",
        "data/base_automation.xml",
    ],
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
