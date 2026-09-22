{
    "name": "HR Employee Name Search",
    "version": "16.0.1.0.0",
    "summary": """ Search employees by academic standing title and full name """,
    "author": "nopparuts, Aginix Technologies",
    "website": "https://github.com/aginix/kmitl-odoo",
    "category": "Human Resources",
    "depends": [
        "hr_employee_academic_standing_thailand",
        "kmitl_hr_employee_full_name",
    ],
    "data": [
        "views/hr_employee_views.xml",
    ],
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
