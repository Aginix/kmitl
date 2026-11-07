{
    "name": "KMITL Project — Portal",
    "summary": "Portal pages for โครงการ/กิจกรรม: public and my-project lists, "
    "project detail and the project dashboard",
    "version": "16.0.1.0.0",
    "category": "Project",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "license": "LGPL-3",
    "depends": ["kmitl_project", "portal"],
    "data": [
        "views/portal_templates.xml",
        "views/portal_dashboard_templates.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "kmitl_project_portal/static/src/scss/project.scss",
            "kmitl_project_portal/static/src/scss/dashboard.scss",
            "kmitl_project_portal/static/src/js/dashboard.js",
        ],
    },
    "installable": True,
    "auto_install": True,
}
