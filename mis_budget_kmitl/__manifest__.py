# -*- coding: utf-8 -*-
{
    "name": "MIS Budget KMITL",
    "version": "16.0.1.0.0",
    "summary": """ MIS Budget KMITL Summary """,
    "category": "KMITL",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "depends": ["base", "budget", "mis_builder"],
    "data": [
        "data/mis.report.style.csv",
        "views/budget_template_server_action.xml",
        "views/mis_budget_report_mis_report_instance_views.xml"
    ],
    "application": False,
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
