# -*- coding: utf-8 -*-
{
    "name": "KMITL User Provisioning",
    "version": "16.0.1.0.0",
    "category": "KMITL",
    "summary": "Gate un-provisioned internal users with a 'contact admin' landing page",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "depends": [
        "hr",
        "web",
    ],
    "data": [
        "views/provisioning_notice_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "kmitl_user_provisioning/static/src/**/*",
        ],
    },
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
