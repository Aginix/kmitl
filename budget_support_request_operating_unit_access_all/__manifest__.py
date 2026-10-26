# -*- coding: utf-8 -*-
{
    "name": "KMITL Budget Support Request — Operating Unit Access All",
    "version": "16.0.1.0.0",
    "summary": """ Let 'Access all OUs' Budget' users see support requests from every OU """,
    "category": "KMITL/Budgeting",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "depends": [
        "budget_support_request_operating_unit",
        "budget_operating_unit_access_all",
    ],
    "data": [
        "security/budget_security.xml",
    ],
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
