# -*- coding: utf-8 -*-
{
    "name": "Budget Account Portal",
    "version": "16.0.1.0.0",
    "author": "",
    "website": "",
    "category": "",
    "depends": ["budget", "web", "portal", "procurement_plan_budget"],
    "data": ["views/portal_templates.xml", "views/budget_account_views.xml"],
    "assets": {
        "web.assets_frontend": ["/budget_account_portal/static/src/scss/portal.scss"],
        "web.assets_backend": [
            "/budget_account_portal/static/src/components/open_portal/open_portal.js",
            "/budget_account_portal/static/src/components/open_portal/open_portal.xml",
        ],
    },
    "application": False,
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
