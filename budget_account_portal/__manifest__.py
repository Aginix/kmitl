# -*- coding: utf-8 -*-
{
    "name": "Budget Account Portal",
    "version": "16.0.1.0.0",
    "author": "",
    "website": "",
    "category": "",
    "depends": ["budget", "web", "portal", "procurement_plan_budget"],
    "data": ["views/portal_templates.xml"],
    "assets": {
        "web.assets_backend": ["budget_account_portal/static/src/**/*"],
    },
    "application": False,
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
