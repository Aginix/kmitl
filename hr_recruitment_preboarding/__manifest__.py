# -*- coding: utf-8 -*-
{
    "name": "HR Recruitment Pre-boarding",
    "version": "16.0.1.0.0",
    "author": "",
    "website": "",
    "category": "KMITL",
    "depends": ["hr_recruitment", "portal", "mail"],
    "data": [
        "security/ir.model.access.csv",
        "data/mail_template.xml",
        "views/hr_preboarding_views.xml",
        "views/hr_applicant_views.xml",
        "views/portal_preboarding_templates.xml",
    ],
    "application": False,
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
