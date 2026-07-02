# -*- coding: utf-8 -*-
{
    "name": "KRIS Project - Extra Allocation",
    "version": "16.0.1.0.0",
    "category": "KMITL",
    "summary": "Support multiple extra payees per KRIS project",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "depends": [
        "kris_project",
    ],
    "data": [
        "data/kris_project_exception_data.xml",
        "views/kris_project_views.xml",
    ],
    "post_init_hook": "post_init_copy_extra_payees",
    "installable": True,
    "application": False,
    "auto_install": False,
    "license": "LGPL-3",
}
