# -*- coding: utf-8 -*-
{
    "name": "Purchase Work Acceptance Todo",
    "version": "16.0.1.0.0",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "KMITL",
    "summary": "Route work.acceptance tier reviews to the unified "
    "mail_activity_todo inbox via base.automation.",
    "depends": [
        "purchase_work_acceptance_tier_validation",
        "mail_activity_todo",
        "base_automation",
    ],
    "data": [
        "data/mail_activity_type.xml",
        "data/base_automation.xml",
    ],
    "installable": True,
    "auto_install": True,
    "license": "LGPL-3",
}
