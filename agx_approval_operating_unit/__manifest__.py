# -*- coding: utf-8 -*-
{
    "name": "Aginix Approval Operating Unit",
    "version": "16.0.1.0.0",
    "summary": "Add Operating Unit support to Aginix Approval Requests",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "KMITL",
    "depends": ["agx_approval", "operating_unit"],
    "data": [
        "security/agx_approval_operating_unit.xml",
        "views/approval_request_views.xml",
    ],
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
