{
    "name": "HR Employee Decoration",
    "version": "16.0.1.2.1",
    "category": "Human Resources",
    "website": "https://github.com/aginix/kmitl-odoo",
    "author": "nopparuts, Aginix Technologies",
    "maintainers": ["nopparuts"],
    "license": "AGPL-3",
    "installable": True,
    "application": False,
    "summary": "Allows storing information about employee decoration in KMITL",
    "description": "Allows storing information about employee decoration in KMITL",
    "depends": ["hr", "office_order", "hr_employee_security_role"],
    "assets": {
        "web.assets_backend": [
            "hr_employee_decoration/static/src/css/*.css",
        ],
    },
    "data": [
        "data/master_data_decoration_relation.xml",
        "security/ir.model.access.csv",
        "views/hr_employee.xml",
        "views/hr_employee_decoration_views.xml",
        "views/hr_employee_decoration_relation.xml",
        "views/hr_menus.xml",
    ],
}
