{
    "name": "KMITL Project Portal Dashboard",
    "version": "16.0.1.0.0",
    "category": "Project",
    "summary": "Public dashboard for KMITL projects",
    "author": "Aginix Technologies",
    "website": "https://github.com/AginixTechnologies/kmitl",
    "depends": [
        "kmitl_project",
        "portal",
        "account_analytic_kmitl",
        "account_fiscal_year",
    ],
    "data": [
        "views/portal_templates.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "kmitl_project_portal_dashboard/static/src/scss/dashboard.scss",
            "kmitl_project_portal_dashboard/static/src/js/dashboard.js",
        ],
    },
    "application": False,
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
