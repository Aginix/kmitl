{
    "name": "HR Employee Name Title KMITL",
    "version": "16.0.1.0.0",
    "summary": """ Compose the employee name from the work-track title prefix and name parts """,
    "author": "nopparuts, Aginix Technologies",
    "website": "https://github.com/aginix/kmitl-odoo",
    "category": "Human Resources",
    "depends": [
        "kmitl_hr_employee_full_name",
        "hr_employee_academic_standing_thailand",
        "hr_employee_education_history",
    ],
    "data": [],
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
    "post_init_hook": "post_init_hook",
}
