# Copyright 2026 Aginix Technologies
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
{
    "name": "Identity & Access Management",
    "version": "16.0.1.0.0",
    "summary": "Standalone app to manage backend users, roles, groups, "
    "access rights and record rules without granting full Settings access",
    "author": "Aginix Technologies",
    "website": "https://github.com/Aginix/kmitl",
    "category": "Administration",
    "license": "LGPL-3",
    "depends": [
        "base",
        "base_user_role",
        "base_user_role_history",
        "base_user_effective_permissions",
    ],
    "data": [
        "security/iam_security.xml",
        "views/iam_menus.xml",
        "views/iam_audit.xml",
        "views/res_users.xml",
    ],
    "application": True,
    "installable": True,
}
