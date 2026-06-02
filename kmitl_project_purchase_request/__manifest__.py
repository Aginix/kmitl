# -*- coding: utf-8 -*-
{
    "name": "KMITL Project Purchase Request",
    "version": "16.0.1.0.0",
    "category": "KMITL",
    "summary": "Create purchase requests (พ.1) from a KMITL project's reserved budget",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "depends": ["kmitl_project", "purchase_request_budget"],
    "data": [
        "views/purchase_request_views.xml",
        "views/kmitl_project_views.xml",
    ],
    "application": False,
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
