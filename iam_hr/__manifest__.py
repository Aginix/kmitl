# Copyright 2026 Aginix Technologies
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
{
    "name": "IAM - HR Departments",
    "version": "16.0.1.1.0",
    "summary": "Browse backend users by HR department and by employee link, "
    "and list employees with/without a linked user, from the Identity & Access app",
    "author": "Aginix Technologies",
    "website": "https://github.com/Aginix/kmitl",
    "category": "Administration",
    "license": "LGPL-3",
    "depends": [
        "iam",
        "hr",
    ],
    "data": [
        "views/iam_hr_department_views.xml",
        "views/iam_hr_employee_views.xml",
        "views/res_users_views.xml",
        "views/iam_hr_menus.xml",
    ],
    "installable": True,
}
