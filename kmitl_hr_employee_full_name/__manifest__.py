{
    "name": "KMITL HR Employee Full Name",
    "version": "16.0.1.2.3",
    "summary": "KMITL HR Employee Full Name",
    "author": "Nopparut, Aginix Technologies",
    "maintainers": ["nopparuts"],
    "website": "",
    "license": "LGPL-3",
    "category": "",
    "depends": ["base", "hr"],
    "data": [
        "security/ir.model.access.csv",
        "data/hr.employee.prefix.csv",
        "views/hr_employee_prefix.xml",
        "views/hr_employee.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "/kmitl_hr_employee_full_name/static/src/scss/kmitl_hr_employee_full_name.scss",
        ],
    },
    "auto_install": False,
    "application": False,
    "post_init_hook": "post_init_hook",
}
