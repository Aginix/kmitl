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
        "data/ir_actions_client.xml",
        "data/ir_config_parameter.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "iam_no_role_landing/static/src/js/no_role_landing.js",
            "iam_no_role_landing/static/src/xml/no_role_landing.xml",
            "iam_no_role_landing/static/src/scss/no_role_landing.scss",
        ],
    },
    "installable": True,
    "application": False,
}
