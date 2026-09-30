{
    "name": "HR Employee Relatives",
    "version": "16.0.1.0.2",
    "category": "Human Resources",
    "website": "https://github.com/aginix/kmitl-odoo",
    "author": "nopparuts, Nonpawit, Aginix Technologies",
    "maintainers": ["n3n", "nopparuts"],
    "license": "AGPL-3",
    "installable": True,
    "application": False,
    "summary": "Allows storing information about employee's family",
    "depends": ["hr", "kmitl_hr_employee_full_name"],
    "external_dependencies": {"python": ["dateutil"]},
    "assets": {
        "web.assets_backend": [
            "hr_employee_relative/static/src/css/*.css",
        ],
    },
    "data": [
        "data/data_relative_relation.xml",
        "security/ir.model.access.csv",
        "views/hr_employee.xml",
        "views/hr_employee_relative.xml",
        "views/hr_employee_relative_relation.xml",
    ],
}
