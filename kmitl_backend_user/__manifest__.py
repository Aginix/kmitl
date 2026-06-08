# Copyright 2026 Aginix Technologies
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
{
    "name": "KMITL Backend User Defaults",
    "version": "16.0.1.0.0",
    "summary": "New users default to a restricted 'Backend UI user' and land "
    "on a Contact-Administrator page until access is granted",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "KMITL/Administration",
    "license": "LGPL-3",
    # base_group_backend (OCA/server-backend) is development_status=Alpha
    # upstream; it provides the "Backend UI user" group + menu restriction.
    "depends": [
        "base_group_backend",
        "web",
    ],
    "data": [
        "views/contact_admin_action.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "kmitl_backend_user/static/src/contact_admin/contact_admin.js",
            "kmitl_backend_user/static/src/contact_admin/contact_admin.xml",
            "kmitl_backend_user/static/src/contact_admin/contact_admin.scss",
        ],
    },
    "application": False,
    "installable": True,
}
