{
    "name": "Procurement Plan Portal",
    "version": "16.0.1.2.0",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "KMITL",
    "depends": [
        "portal",
        "procurement_plan",
        "procurement_plan_budget",
        "purchase_request_procurement_plan",
    ],
    "data": ["views/templates.xml"],
    "assets": {
        "web.assets_frontend": ["/procurement_plan_portal/static/src/scss/portal.scss"],
    },
    "application": False,
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
