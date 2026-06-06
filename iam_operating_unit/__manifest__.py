# Copyright 2026 Aginix Technologies
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
{
    "name": "IAM - Operating Units",
    "version": "16.0.1.0.0",
    "summary": "Manage Operating Units from the Identity & Access app",
    "author": "Aginix Technologies",
    "website": "https://github.com/Aginix/kmitl",
    "category": "Administration",
    "license": "LGPL-3",
    "depends": [
        "iam",
        "operating_unit",
    ],
    "data": [
        "security/iam_operating_unit_security.xml",
        "security/ir.model.access.csv",
        "views/iam_operating_unit_menus.xml",
        "views/operating_unit_views.xml",
        "views/res_users_views.xml",
    ],
    "installable": True,
}
