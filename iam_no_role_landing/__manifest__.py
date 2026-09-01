# Copyright 2026 Aginix Technologies
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
{
    "name": "IAM — No-Role Landing",
    "version": "16.0.1.0.0",
    "summary": "Gate role-less backend users behind a friendly landing page",
    "author": "Aginix Technologies",
    "website": "https://github.com/Aginix/kmitl",
    "category": "Administration",
    "license": "LGPL-3",
    "depends": [
        "iam",
        "base_user_role",
    ],
    "data": [
        "data/ir_config_parameter.xml",
        "views/no_role_templates.xml",
    ],
    "installable": True,
    "application": False,
}
