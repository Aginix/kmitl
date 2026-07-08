# -*- coding: utf-8 -*-
{
    "name": "Base Assignment",
    "version": "16.0.1.0.0",
    "summary": "Reusable Assigned Officer mixin — auto-injected Assign to me / "
    "Assign… / Unassign alert above the sheet",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "Tools",
    "depends": [
        "mail",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/mail_activity_type.xml",
        "templates/assignment_templates.xml",
        "wizards/assign_officer_wizard_views.xml",
    ],
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
