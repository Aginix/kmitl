{
    "name": "HR Employee KMITL KID",
    "version": "16.0.1.0.1",
    "summary": """ HR Employee KMITL KID Summary """,
    "author": "nopparuts, Aginix Technologies",
    "website": "https://github.com/aginix/kmitl-odoo",
    "category": "Human Resources",
    "depends": [
        "hr",
    ],
    "data": ["data/ir_sequence.xml", "views/hr_view_employee_form_views.xml"],
    "post_init_hook": "post_init_hook",
    "application": True,
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
