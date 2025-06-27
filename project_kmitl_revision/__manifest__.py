{
    "name": "KMITL Project Revision",
    "version": "16.0.1.0.0",
    "summary": """ Project KMITL Revision""",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "KMITL/Project",
    "depends": ["base", "web", "base_revision", "project_kmitl"],
    "data": [
        "security/ir.model.access.csv",
        "views/project_project_views.xml",
        "wizards/project_revision_confirm_wizard.xml",
    ],
    "assets": {
        "web.assets_backend": ["project_kmitl_revision/static/src/**/*"],
    },
    "application": False,
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
