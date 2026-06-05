{
    "name": "HR Employee Name Detail KMITL",
    "version": "16.0.1.0.0",
    "summary": """ Show academic standing, email, department and KID
        under hr.employee many2one fields """,
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl-odoo",
    "category": "Human Resources",
    "depends": [
        "hr",
        "hr_department_code_tracking",
        "hr_employee_academic_standing_thailand",
        "hr_employee_kmitl_kid",
    ],
    "data": [],
    "assets": {
        "web.assets_backend": [
            "hr_employee_name_detail_kmitl/static/src/**/*.js",
            "hr_employee_name_detail_kmitl/static/src/**/*.xml",
            "hr_employee_name_detail_kmitl/static/src/**/*.scss",
        ],
    },
    "application": False,
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
