{
    "name": "HR Employee Academic Standing Thailand - Dr. Auto",
    "version": "16.0.1.0.0",
    "summary": """ Auto-tick the ดร./Dr. flag from the employee's education history """,
    "author": "nopparuts, Aginix Technologies",
    "website": "https://github.com/aginix/kmitl-odoo",
    "category": "Human Resources",
    "depends": [
        "hr_employee_academic_standing_thailand",
        "hr_employee_education_history",
    ],
    "data": [],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
