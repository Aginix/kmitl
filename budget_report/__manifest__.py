# -*- coding: utf-8 -*-
{
    'name': 'Budget Report',
    "version": "16.0.1.0.0",
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
            "budget_report/static/src/**/*",
        ],
    },
    "auto_install": False,
    "application": False,
    "installable": True,
    "license": "AGPL-3",
}
