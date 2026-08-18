# -*- coding: utf-8 -*-
{
    "name": "Procurement Plan Portal",
    "version": "16.0.1.1.0",
    "author": "",
    "website": "",
    "category": "",
    "depends": ["portal", "procurement_plan", "purchase_request_procurement_plan"],
    "data": ["views/templates.xml"],
    "assets": {
        "web.assets_frontend": [
            "/procurement_plan_portal/static/src/scss/portal.scss"
        ],
    },
    "application": False,
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
