# -*- coding: utf-8 -*-
{
    "name": "KMITL Project Disbursement",
    "version": "16.0.1.0.0",
    "category": "KMITL",
    "summary": "Create disbursement requests (ใบขอเบิก) for a KMITL project's "
    "non-purchase expenses, drawn from its reserved budget",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "depends": ["kmitl_project", "disbursement"],
    "data": [
        "security/ir.model.access.csv",
        "security/security.xml",
        "views/kmitl_project_views.xml",
        "views/disbursement_request_views.xml",
    ],
    "application": False,
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
