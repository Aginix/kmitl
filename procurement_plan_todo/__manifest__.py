{
    "name": "Procurement Plan Todos",
    "version": "16.0.1.0.0",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "KMITL",
    "summary": "Route a 'complete the operating plan' Todo to the plan officers "
    "of the plan's operating unit (UC1)",
    "depends": [
        "mail_activity_todo_role_unit",
        "procurement_plan_operating_unit",
    ],
    "data": [
        "data/res_users_role.xml",
        "data/mail_activity_type.xml",
        "views/procurement_plan_views.xml",
    ],
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
