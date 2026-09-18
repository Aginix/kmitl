# -*- coding: utf-8 -*-
{
    'name': 'Budget Report',
    "version": "16.0.1.0.1",
    "summary": "Budget Report",
    "category": "KMITL/Budgeting",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "depends": ["budget", "web"],
    "data": [
        "data/actions.xml",
        "security/ir.model.access.csv",
        "views/menus.xml"
    ],
    "assets": {
        "web.assets_backend": [
            "budget_report/static/src/components/budget_report_summary/budget_report_summary.js",
            "budget_report/static/src/components/budget_report_summary/budget_report_summary.xml",
            "budget_report/static/src/components/budget_report_summary/budget_report_summary.scss",
            "budget_report/static/src/components/department_filter/department_filter.js",
            "budget_report/static/src/components/department_filter/department_filter.xml",
            "budget_report/static/src/components/department_filter/department_filter.scss",
        ],
    },
    "auto_install": False,
    "application": False,
    "installable": True,
    "license": "AGPL-3",
}
